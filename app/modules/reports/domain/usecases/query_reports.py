# app/modules/reports/domain/usecases/query_reports.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError
from app.modules.reports.domain.repo import AcceptanceReportRepo, ReportSourceRepo


@dataclass(frozen=True)
class ReportWithEmail:
    report: AcceptanceReport
    email: Optional[str]


@dataclass(frozen=True)
class ListReportsUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo
    source_repo: ReportSourceRepo

    async def execute(
        self, *, period: Optional[str], status: Optional[ReportStatus],
        creator_user_id: Optional[str],
    ) -> list[ReportWithEmail]:
        reports = await self.report_repo.list(
            period=period,
            statuses=[status] if status is not None else None,
            creator_user_id=creator_user_id,
        )
        reports.sort(key=lambda r: r.created_at, reverse=True)  # newest first
        emails = await self.source_repo.creator_emails(
            {r.creator_user_id for r in reports}
        )
        return [ReportWithEmail(report=r, email=emails.get(r.creator_user_id)) for r in reports]


@dataclass(frozen=True)
class ListMyReportsUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo

    async def execute(self, *, creator_user_id: str) -> list[AcceptanceReport]:
        reports = await self.report_repo.list(
            period=None,
            statuses=[ReportStatus.FINAL, ReportStatus.AMENDED],
            creator_user_id=creator_user_id,
        )
        reports.sort(key=lambda r: r.created_at, reverse=True)  # newest first
        return reports


@dataclass(frozen=True)
class GetReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo

    async def execute(self, *, report_id: str) -> AcceptanceReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()
        return report
