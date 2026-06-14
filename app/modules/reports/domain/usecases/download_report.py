# app/modules/reports/domain/usecases/download_report.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError
from app.modules.reports.domain.repo import AcceptanceReportRepo
from app.modules.reports.storage import ObjectStorage


@dataclass(frozen=True)
class DownloadReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo
    storage: ObjectStorage

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
        filename = f"bien-ban-nghiem-thu-{report.period}-{report.id}.docx"
        return filename, data
