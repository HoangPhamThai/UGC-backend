# app/modules/reports/domain/usecases/delete_report.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError, ReportStateConflictError
from app.modules.reports.domain.repo import AcceptanceReportRepo
from app.modules.reports.storage import ObjectStorage
from app.modules.workspaces.domain.repo import ArticleRepo


@dataclass(frozen=True)
class DeleteReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo
    article_repo: ArticleRepo
    storage: ObjectStorage

    async def execute(self, *, report_id: str) -> None:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()
        if report.status != ReportStatus.DRAFT:
            raise ReportStateConflictError("Only a draft report can be deleted")

        for li in report.line_items:
            await self.article_repo.set_report_id(li.article_id, None)
        try:
            await self.storage.delete(report.object_key)
        except Exception:  # noqa: BLE001 — object may already be gone
            self.log_warning(f"Object delete failed (ignored): {report.object_key}")
        await self.report_repo.delete(report_id)
