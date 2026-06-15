import pytest

from app.modules.reports.data.model import AcceptanceReport, LineItem, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError, ReportStateConflictError
from app.modules.reports.domain.usecases.cancel_report import CancelReportUseCase
from app.modules.reports.domain.usecases.generate_reports import GenerateReportsUseCase
from app.modules.reports.storage import InMemoryObjectStorage
from app.modules.workspaces.data.model import ArticleStatus
from app.modules.profiles.data.model import CreatorProfile, REQUIRED_PROFILE_FIELDS
from tests.conftest import FakeArticleRepo, make_article
from tests.profiles.test_usecases import FakeProfileRepo
from tests.reports.fakes import (
    FakeAcceptanceReportRepo, FakeReportSourceRepo, FakeTemplateRepo, make_eligible,
)


def _final_report() -> AcceptanceReport:
    return AcceptanceReport(
        id="rpt_1", period="2026-06", creator_user_id="u_a", created_by="u_admin",
        status=ReportStatus.FINAL,
        line_items=[LineItem(article_id="art_1", seq=1, on_air_date="2026-06-01")],
        object_key="reports/2026-06/rpt_1.docx",
    )


@pytest.mark.asyncio
async def test_cancel_final_sets_amended_and_unlocks_articles():
    art = make_article(status=ArticleStatus.APPROVED, aid="art_1")
    art.report_id = "rpt_1"
    arts = FakeArticleRepo([art])
    repo = FakeAcceptanceReportRepo([_final_report()])
    uc = CancelReportUseCase(report_repo=repo, article_repo=arts)
    out = await uc.execute(report_id="rpt_1", cancelled_by="u_admin")
    assert out.status == ReportStatus.AMENDED
    assert out.cancelled_by == "u_admin"
    assert art.report_id is None  # unlocked, eligible again


@pytest.mark.asyncio
async def test_cancel_non_final_rejected():
    r = _final_report()
    r.status = ReportStatus.DRAFT
    uc = CancelReportUseCase(report_repo=FakeAcceptanceReportRepo([r]), article_repo=FakeArticleRepo([]))
    with pytest.raises(ReportStateConflictError):
        await uc.execute(report_id="rpt_1", cancelled_by="u_admin")


@pytest.mark.asyncio
async def test_cancel_missing_rejected():
    uc = CancelReportUseCase(report_repo=FakeAcceptanceReportRepo([]), article_repo=FakeArticleRepo([]))
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id="nope", cancelled_by="u_admin")


@pytest.mark.asyncio
async def test_generate_after_cancel_recreates_for_same_period():
    # An amended report for (u_a, 2026-06) must NOT block a new report for the same slot.
    amended = _final_report()
    amended.status = ReportStatus.AMENDED
    storage = InMemoryObjectStorage()

    def fake_render(*, scalars, line_items, template_bytes=None):
        return b"DOCX"

    gen = GenerateReportsUseCase(
        report_repo=FakeAcceptanceReportRepo([amended]),
        source_repo=FakeReportSourceRepo(eligible=[make_eligible("art_1", "u_a")]),
        profile_repo=FakeProfileRepo([CreatorProfile(user_id="u_a", **{f: "x" for f in REQUIRED_PROFILE_FIELDS})]),
        article_repo=FakeArticleRepo([make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")]),
        storage=storage, render=fake_render, template_repo=FakeTemplateRepo(None),
    )
    created = await gen.execute(
        period="2026-06", article_award_price=1, tax_rate=0.0, created_by="u_admin", creator_user_id="u_a",
    )
    assert len(created) == 1 and created[0].status == ReportStatus.DRAFT
