# app/modules/reports/domain/usecases/report_statistics.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import ReportStatus
from app.modules.reports.domain.repo import AcceptanceReportRepo


@dataclass(frozen=True)
class ReportStatistics:
    period: Optional[str]
    draft_count: int
    final_count: int
    creator_count: int
    total_final_award: int


@dataclass(frozen=True)
class ReportStatisticsUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo

    async def execute(self, *, period: Optional[str] = None) -> ReportStatistics:
        reports = await self.report_repo.list(
            period=period, statuses=None, creator_user_id=None
        )
        drafts = [r for r in reports if r.status == ReportStatus.DRAFT]
        finals = [r for r in reports if r.status == ReportStatus.FINAL]
        creators = {r.creator_user_id for r in reports}
        return ReportStatistics(
            period=period,
            draft_count=len(drafts),
            final_count=len(finals),
            creator_count=len(creators),
            total_final_award=sum(r.final_award for r in finals),
        )
