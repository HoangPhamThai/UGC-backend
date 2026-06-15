import pytest
from app.modules.reports.data.model import ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError
from app.modules.reports.domain.usecases.get_my_report import GetMyReportUseCase
from app.modules.reports.domain.usecases.query_reports import ListMyReportsUseCase
from tests.reports.fakes import FakeAcceptanceReportRepo
from tests.reports.test_model import _report


@pytest.mark.asyncio
async def test_get_my_report_returns_own_report():
    r = _report()
    uc = GetMyReportUseCase(report_repo=FakeAcceptanceReportRepo([r]))
    found = await uc.execute(report_id=r.id, creator_user_id=r.creator_user_id)
    assert found.id == r.id


@pytest.mark.asyncio
async def test_get_my_report_raises_for_wrong_creator():
    r = _report()
    uc = GetMyReportUseCase(report_repo=FakeAcceptanceReportRepo([r]))
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id=r.id, creator_user_id="wrong")


@pytest.mark.asyncio
async def test_list_my_reports_includes_draft_reviewing_final():
    # Each report needs a unique period to avoid ID collisions in the fake
    reports = [
        _report(period="2026-06", status=ReportStatus.DRAFT),
        _report(period="2026-05", status=ReportStatus.REVIEWING),
        _report(period="2026-04", status=ReportStatus.FINAL),
        _report(period="2026-03", status=ReportStatus.AMENDED),
    ]
    uc = ListMyReportsUseCase(report_repo=FakeAcceptanceReportRepo(reports))
    result = await uc.execute(creator_user_id="u_creator")
    statuses = {r.status for r in result}
    assert ReportStatus.DRAFT in statuses
    assert ReportStatus.REVIEWING in statuses
    assert ReportStatus.FINAL in statuses
    assert ReportStatus.AMENDED not in statuses
