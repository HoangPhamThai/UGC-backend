import pytest

from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError
from app.modules.reports.domain.usecases.download_report import DownloadReportUseCase
from app.modules.reports.domain.usecases.query_reports import (
    GetReportUseCase,
    ListMyReportsUseCase,
    ListReportsUseCase,
)
from app.modules.reports.storage import InMemoryObjectStorage
from tests.reports.fakes import FakeAcceptanceReportRepo


def _r(rid, creator, status, period="2026-06") -> AcceptanceReport:
    return AcceptanceReport(
        id=rid, period=period, creator_user_id=creator, created_by="u_admin",
        status=status, object_key=f"reports/{period}/{rid}.docx",
    )


@pytest.mark.asyncio
async def test_list_my_returns_only_own_finals():
    repo = FakeAcceptanceReportRepo([
        _r("rpt_1", "u_a", ReportStatus.FINAL),
        _r("rpt_2", "u_a", ReportStatus.DRAFT),
        _r("rpt_3", "u_b", ReportStatus.FINAL),
    ])
    uc = ListMyReportsUseCase(report_repo=repo)
    out = await uc.execute(creator_user_id="u_a")
    assert [r.id for r in out] == ["rpt_1"]


@pytest.mark.asyncio
async def test_admin_list_filters():
    repo = FakeAcceptanceReportRepo([
        _r("rpt_1", "u_a", ReportStatus.FINAL),
        _r("rpt_2", "u_b", ReportStatus.DRAFT),
    ])
    uc = ListReportsUseCase(report_repo=repo)
    drafts = await uc.execute(period="2026-06", status=ReportStatus.DRAFT, creator_user_id=None)
    assert [r.id for r in drafts] == ["rpt_2"]


@pytest.mark.asyncio
async def test_get_missing_raises():
    uc = GetReportUseCase(report_repo=FakeAcceptanceReportRepo([]))
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id="nope")


@pytest.mark.asyncio
async def test_admin_download_any():
    storage = InMemoryObjectStorage()
    await storage.put("reports/2026-06/rpt_1.docx", b"BYTES", content_type="application/x")
    repo = FakeAcceptanceReportRepo([_r("rpt_1", "u_a", ReportStatus.DRAFT)])
    uc = DownloadReportUseCase(report_repo=repo, storage=storage)
    filename, data = await uc.execute(report_id="rpt_1", require_creator_id=None)
    assert data == b"BYTES" and filename.endswith(".docx")


@pytest.mark.asyncio
async def test_creator_download_blocked_for_draft_or_other():
    storage = InMemoryObjectStorage()
    await storage.put("reports/2026-06/rpt_1.docx", b"BYTES", content_type="application/x")
    repo = FakeAcceptanceReportRepo([
        _r("rpt_1", "u_a", ReportStatus.DRAFT),
        _r("rpt_2", "u_b", ReportStatus.FINAL),
    ])
    uc = DownloadReportUseCase(report_repo=repo, storage=storage)
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id="rpt_1", require_creator_id="u_a")
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id="rpt_2", require_creator_id="u_a")


@pytest.mark.asyncio
async def test_creator_download_own_final_ok():
    storage = InMemoryObjectStorage()
    await storage.put("reports/2026-06/rpt_1.docx", b"OK", content_type="application/x")
    repo = FakeAcceptanceReportRepo([_r("rpt_1", "u_a", ReportStatus.FINAL)])
    uc = DownloadReportUseCase(report_repo=repo, storage=storage)
    _, data = await uc.execute(report_id="rpt_1", require_creator_id="u_a")
    assert data == b"OK"
