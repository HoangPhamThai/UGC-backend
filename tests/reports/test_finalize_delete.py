import pytest

from app.modules.reports.data.model import AcceptanceReport, LineItem, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError, ReportStateConflictError
from app.modules.reports.domain.usecases.delete_report import DeleteReportUseCase
from app.modules.reports.domain.usecases.finalize_report import FinalizeReportUseCase
from app.modules.reports.storage import InMemoryObjectStorage
from app.modules.workspaces.data.model import ArticleStatus
from tests.conftest import FakeArticleRepo, make_article
from tests.reports.fakes import FakeAcceptanceReportRepo

COMPLETE_SNAPSHOT = {
    "full_name": "A", "date_of_birth": "x", "social_id": "x",
    "social_id_date_of_issue": "x", "social_id_place_of_issue": "x",
    "primary_address": "x", "tax_number": "x", "bank_account_number": "x",
    "bank_name": "x", "bank_branch": "x",
}


def _report(status=ReportStatus.DRAFT, snapshot=None) -> AcceptanceReport:
    return AcceptanceReport(
        id="rpt_1", period="2026-06", creator_user_id="u_a", created_by="u_admin",
        status=status, creator_snapshot=snapshot if snapshot is not None else COMPLETE_SNAPSHOT,
        line_items=[LineItem(article_id="art_1", seq=1, on_air_date="2026-06-01")],
        object_key="reports/2026-06/rpt_1.docx",
    )


@pytest.mark.asyncio
async def test_finalize_draft_with_complete_snapshot():
    repo = FakeAcceptanceReportRepo([_report()])
    uc = FinalizeReportUseCase(report_repo=repo)
    out = await uc.execute(report_id="rpt_1", finalized_by="u_admin")
    assert out.status == ReportStatus.FINAL


@pytest.mark.asyncio
async def test_finalize_blocks_incomplete_snapshot():
    repo = FakeAcceptanceReportRepo([_report(snapshot={"full_name": "A"})])
    uc = FinalizeReportUseCase(report_repo=repo)
    with pytest.raises(ReportStateConflictError):
        await uc.execute(report_id="rpt_1", finalized_by="u_admin")


@pytest.mark.asyncio
async def test_finalize_non_draft_rejected():
    repo = FakeAcceptanceReportRepo([_report(status=ReportStatus.FINAL)])
    uc = FinalizeReportUseCase(report_repo=repo)
    with pytest.raises(ReportStateConflictError):
        await uc.execute(report_id="rpt_1", finalized_by="u_admin")


@pytest.mark.asyncio
async def test_delete_draft_unlocks_articles_and_removes_object():
    art = make_article(status=ArticleStatus.APPROVED, aid="art_1")
    art.report_id = "rpt_1"
    arts = FakeArticleRepo([art])
    storage = InMemoryObjectStorage()
    await storage.put("reports/2026-06/rpt_1.docx", b"x", content_type="application/x")
    repo = FakeAcceptanceReportRepo([_report()])
    uc = DeleteReportUseCase(report_repo=repo, article_repo=arts, storage=storage)
    await uc.execute(report_id="rpt_1")
    assert art.report_id is None
    assert await repo.get_by_id("rpt_1") is None
    with pytest.raises(KeyError):
        await storage.get("reports/2026-06/rpt_1.docx")


@pytest.mark.asyncio
async def test_delete_final_rejected():
    repo = FakeAcceptanceReportRepo([_report(status=ReportStatus.FINAL)])
    uc = DeleteReportUseCase(
        report_repo=repo, article_repo=FakeArticleRepo([]), storage=InMemoryObjectStorage()
    )
    with pytest.raises(ReportStateConflictError):
        await uc.execute(report_id="rpt_1")


@pytest.mark.asyncio
async def test_delete_missing_rejected():
    uc = DeleteReportUseCase(
        report_repo=FakeAcceptanceReportRepo([]),
        article_repo=FakeArticleRepo([]), storage=InMemoryObjectStorage(),
    )
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id="nope")
