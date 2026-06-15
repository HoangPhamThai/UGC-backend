from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import AcceptanceReport
from app.modules.reports.domain.errors import ReportNotFoundError
from app.modules.reports.domain.repo import AcceptanceReportRepo


@dataclass(frozen=True)
class GetMyReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo

    async def execute(self, *, report_id: str, creator_user_id: str) -> AcceptanceReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None or report.creator_user_id != creator_user_id:
            raise ReportNotFoundError()
        return report
