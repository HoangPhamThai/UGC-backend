from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import (
    ReportNotFoundError, ReportStateConflictError, ReportValidationError,
)
from app.modules.reports.domain.repo import AcceptanceReportRepo


@dataclass(frozen=True)
class SubmitReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo

    async def execute(self, *, report_id: str, submitter_user_id: str) -> AcceptanceReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None or report.creator_user_id != submitter_user_id:
            raise ReportNotFoundError()
        if report.status != ReportStatus.DRAFT:
            raise ReportStateConflictError("Only draft reports can be submitted")

        missing = [li.article_id for li in report.line_items if not li.article_image]
        if missing:
            raise ReportValidationError(f"Missing images for articles: {', '.join(missing)}")

        submitted = await self.report_repo.submit(report_id)
        if submitted is None:
            raise ReportNotFoundError()
        return submitted
