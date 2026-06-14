# app/modules/reports/domain/usecases/query_reports.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError
from app.modules.reports.domain.repo import AcceptanceReportRepo


@dataclass(frozen=True)
class ListReportsUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo

    async def execute(
        self, *, period: Optional[str], status: Optional[ReportStatus],
        creator_user_id: Optional[str],
    ) -> list[AcceptanceReport]:
        return await self.report_repo.list(
            period=period, status=status, creator_user_id=creator_user_id
        )


@dataclass(frozen=True)
class ListMyReportsUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo

    async def execute(self, *, creator_user_id: str) -> list[AcceptanceReport]:
        return await self.report_repo.list(
            period=None, status=ReportStatus.FINAL, creator_user_id=creator_user_id
        )


@dataclass(frozen=True)
class GetReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo

    async def execute(self, *, report_id: str) -> AcceptanceReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()
        return report
