# app/modules/reports/domain/usecases/template.py
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.domain.repo import TemplateRepo
from app.modules.reports.rendering import TEMPLATE_PATH, validate_template_bytes

_DEFAULT_FILENAME = "acceptance_report_template.docx"


@dataclass(frozen=True)
class TemplateView:
    filename: str
    uploaded_by: Optional[str]
    uploaded_at: Optional[datetime]
    is_default: bool


@dataclass(frozen=True)
class GetTemplateUseCase(LoggerMixin):
    template_repo: TemplateRepo

    async def execute(self) -> TemplateView:
        meta = await self.template_repo.get_meta()
        if meta is None:
            return TemplateView(
                filename=_DEFAULT_FILENAME, uploaded_by=None, uploaded_at=None, is_default=True
            )
        return TemplateView(
            filename=meta.filename, uploaded_by=meta.uploaded_by,
            uploaded_at=meta.uploaded_at, is_default=False,
        )


@dataclass(frozen=True)
class UploadTemplateUseCase(LoggerMixin):
    template_repo: TemplateRepo

    async def execute(self, *, data: bytes, filename: str, uploaded_by: str) -> TemplateView:
        validate_template_bytes(data)  # raises ReportValidationError on bad input
        meta = await self.template_repo.save(
            data=data, filename=filename, uploaded_by=uploaded_by
        )
        return TemplateView(
            filename=meta.filename, uploaded_by=meta.uploaded_by,
            uploaded_at=meta.uploaded_at, is_default=False,
        )


@dataclass(frozen=True)
class DownloadTemplateUseCase(LoggerMixin):
    template_repo: TemplateRepo

    async def execute(self) -> tuple[str, bytes]:
        data = await self.template_repo.get_active_bytes()
        if data is not None:
            meta = await self.template_repo.get_meta()
            return (meta.filename if meta else _DEFAULT_FILENAME), data
        return _DEFAULT_FILENAME, Path(TEMPLATE_PATH).read_bytes()
