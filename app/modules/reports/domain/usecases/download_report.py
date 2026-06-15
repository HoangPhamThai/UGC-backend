# app/modules/reports/domain/usecases/download_report.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError
from app.modules.reports.domain.repo import AcceptanceReportRepo, ReportSourceRepo
from app.modules.reports.storage import ObjectStorage


@dataclass(frozen=True)
class DownloadReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo
    storage: ObjectStorage
    source_repo: ReportSourceRepo

    async def execute(
        self, *, report_id: str, require_creator_id: Optional[str]
    ) -> tuple[str, bytes]:
        """Return (filename, docx_bytes). When require_creator_id is set (creator
        caller), the report must be that creator's AND final; otherwise (admin)
        any report is downloadable. A scope failure looks like 'not found'."""
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()
        if require_creator_id is not None:
            if (
                report.creator_user_id != require_creator_id
                or report.status != ReportStatus.FINAL
            ):
                raise ReportNotFoundError()

        data = await self.storage.get(report.object_key)
        emails = await self.source_repo.creator_emails({report.creator_user_id})
        email = emails.get(report.creator_user_id)
        local = email.split("@")[0] if email else report.creator_user_id
        year, month_str = report.period.split("-")
        filename = f"{local}_report_{int(month_str)}_{year}.docx"
        return filename, data
