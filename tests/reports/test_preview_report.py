import pytest

from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError
from app.modules.reports.domain.usecases.preview_report import PreviewReportUseCase
from app.modules.reports.storage import InMemoryObjectStorage
from tests.reports.fakes import FakeAcceptanceReportRepo, FakeReportSourceRepo


def _r(rid, creator, status) -> AcceptanceReport:
    return AcceptanceReport(
        id=rid, period="2026-06", creator_user_id=creator, created_by="u_admin",
        status=status, object_key=f"reports/2026-06/{rid}.docx",
    )


async def _uc_with(report) -> PreviewReportUseCase:
    storage = InMemoryObjectStorage()
    await storage.put(report.object_key, b"DOCX", content_type="application/x")
    return PreviewReportUseCase(
        report_repo=FakeAcceptanceReportRepo([report]),
        storage=storage, source_repo=FakeReportSourceRepo(),
    )


@pytest.mark.asyncio
async def test_admin_preview_amended_returns_bytes():
    uc = await _uc_with(_r("rpt_1", "u_a", ReportStatus.AMENDED))
    _, data = await uc.execute(report_id="rpt_1", require_creator_id=None)
    assert data == b"DOCX"


@pytest.mark.asyncio
async def test_creator_preview_own_amended_returns_bytes():
    uc = await _uc_with(_r("rpt_1", "u_a", ReportStatus.AMENDED))
    _, data = await uc.execute(report_id="rpt_1", require_creator_id="u_a")
    assert data == b"DOCX"


@pytest.mark.asyncio
async def test_creator_preview_other_creator_rejected():
    uc = await _uc_with(_r("rpt_1", "u_a", ReportStatus.FINAL))
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id="rpt_1", require_creator_id="u_b")
