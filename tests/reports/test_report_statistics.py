import pytest

from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.usecases.report_statistics import (
    ReportStatisticsUseCase,
)
from tests.reports.fakes import FakeAcceptanceReportRepo


def _r(rid, creator, status, final_award, period="2026-06"):
    return AcceptanceReport(
        id=rid, period=period, creator_user_id=creator, created_by="u_admin",
        status=status, final_award=final_award, object_key=f"k/{rid}.docx",
    )


@pytest.mark.asyncio
async def test_statistics_counts_and_sum():
    repo = FakeAcceptanceReportRepo([
        _r("r1", "u_a", ReportStatus.FINAL, 900_000),
        _r("r2", "u_b", ReportStatus.FINAL, 500_000),
        _r("r3", "u_a", ReportStatus.DRAFT, 100_000),
    ])
    uc = ReportStatisticsUseCase(report_repo=repo)
    s = await uc.execute(period="2026-06")
    assert s.draft_count == 1
    assert s.final_count == 2
    assert s.creator_count == 2
    assert s.total_final_award == 1_400_000
