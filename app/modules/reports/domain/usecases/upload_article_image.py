from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import (
    ReportNotFoundError, ReportStateConflictError, ReportValidationError,
)
from app.modules.reports.domain.repo import AcceptanceReportRepo
from app.modules.reports.storage import ObjectStorage

_EXT_MAP = {
    "image/jpeg": "jpg", "image/jpg": "jpg",
    "image/png": "png", "image/gif": "gif", "image/webp": "webp",
}


def _ext(content_type: str) -> str:
    return _EXT_MAP.get(content_type.split(";")[0].strip().lower(), "jpg")


@dataclass(frozen=True)
class UploadArticleImageUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo
    storage: ObjectStorage

    async def execute(
        self, *, report_id: str, article_id: str,
        image_bytes: bytes, content_type: str, uploader_user_id: str,
    ) -> AcceptanceReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None or report.creator_user_id != uploader_user_id:
            raise ReportNotFoundError()
        if report.status != ReportStatus.DRAFT:
            raise ReportStateConflictError("Only draft reports accept image uploads")
        if not any(li.article_id == article_id for li in report.line_items):
            raise ReportValidationError(f"Article {article_id} not in report")

        ext = _ext(content_type)
        key = f"reports/{report.period}/{report_id}/images/{article_id}.{ext}"
        await self.storage.put(key, image_bytes, content_type=content_type)

        updated = await self.report_repo.update_line_item_image(report_id, article_id, key)
        if updated is None:
            raise ReportNotFoundError()
        return updated
