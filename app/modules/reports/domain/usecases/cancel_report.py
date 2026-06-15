# app/modules/reports/domain/usecases/cancel_report.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError, ReportStateConflictError
from app.modules.reports.domain.repo import AcceptanceReportRepo
from app.modules.workspaces.domain.repo import ArticleRepo


@dataclass(frozen=True)
class CancelReportUseCase(LoggerMixin):
    """Cancel a FINAL report -> status amended. Keeps the stored docx (still
    viewable) but unlocks its articles so they can feed a new report."""
    report_repo: AcceptanceReportRepo
    article_repo: ArticleRepo

    async def execute(self, *, report_id: str, cancelled_by: str) -> AcceptanceReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()
        if report.status != ReportStatus.FINAL:
            raise ReportStateConflictError("Only a final report can be cancelled")
        cancelled = await self.report_repo.cancel(report_id, cancelled_by=cancelled_by)
        if cancelled is None:
            raise ReportNotFoundError()
        for li in report.line_items:
            await self.article_repo.set_report_id(li.article_id, None)
        return cancelled
