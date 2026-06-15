import pytest

from app.modules.profiles.data.model import CreatorProfile, REQUIRED_PROFILE_FIELDS
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportStateConflictError
from app.modules.reports.domain.usecases.delete_report import DeleteReportUseCase
from app.modules.reports.domain.usecases.generate_reports import GenerateReportsUseCase
from app.modules.reports.domain.usecases.regenerate_report import RegenerateReportUseCase
from app.modules.reports.storage import InMemoryObjectStorage
from app.modules.workspaces.data.model import ArticleStatus
from tests.conftest import FakeArticleRepo, make_article
from tests.profiles.test_usecases import FakeProfileRepo
from tests.reports.fakes import (
    FakeAcceptanceReportRepo, FakeReportSourceRepo, FakeTemplateRepo, make_eligible,
)

ALL_REQUIRED = {f: "x" for f in REQUIRED_PROFILE_FIELDS}


def _existing_draft() -> AcceptanceReport:
    return AcceptanceReport(
        id="rpt_old", period="2026-06", creator_user_id="u_a", created_by="u_admin",
        status=ReportStatus.DRAFT, article_award_price=500_000, total_approved_articles=2,
        total_award=1_000_000, tax=50_000, final_award=950_000,
        object_key="reports/2026-06/rpt_old.docx",
    )


def _wire(existing):
    storage = InMemoryObjectStorage()
    report_repo = FakeAcceptanceReportRepo([existing])
    article_repo = FakeArticleRepo([
        make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1"),
    ])

    def fake_render(*, scalars, line_items, template_bytes=None):
        return b"DOCX-BYTES"

    delete_uc = DeleteReportUseCase(report_repo=report_repo, article_repo=article_repo, storage=storage)
    generate_uc = GenerateReportsUseCase(
        report_repo=report_repo,
        source_repo=FakeReportSourceRepo(eligible=[make_eligible("art_1", "u_a")]),
        profile_repo=FakeProfileRepo([CreatorProfile(user_id="u_a", **ALL_REQUIRED)]),
        article_repo=article_repo, storage=storage, render=fake_render,
        template_repo=FakeTemplateRepo(),
    )
    regen = RegenerateReportUseCase(report_repo=report_repo, delete_uc=delete_uc, generate_uc=generate_uc)
    return regen, report_repo


@pytest.mark.asyncio
async def test_regenerate_replaces_draft_reusing_price_and_rate():
    regen, report_repo = _wire(_existing_draft())
    new = await regen.execute(report_id="rpt_old", regenerated_by="u_admin")
    assert new.id != "rpt_old"
    assert new.status == ReportStatus.DRAFT
    assert new.creator_user_id == "u_a"
    assert new.article_award_price == 500_000
    # one eligible article → total 500_000, rate 0.05 → tax 25_000
    assert new.total_approved_articles == 1
    assert new.total_award == 500_000
    assert new.tax == 25_000
    assert "rpt_old" not in report_repo.items  # old draft gone


@pytest.mark.asyncio
async def test_regenerate_rejects_non_draft():
    final = _existing_draft()
    final.status = ReportStatus.FINAL
    regen, _ = _wire(final)
    with pytest.raises(ReportStateConflictError):
        await regen.execute(report_id="rpt_old", regenerated_by="u_admin")
