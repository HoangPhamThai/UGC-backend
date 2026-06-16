# app/modules/reports/domain/usecases/approve_report.py
from dataclasses import dataclass
from typing import Callable, Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.email.messages import ReportEmailEvent
from app.modules.email.service import EmailService
from app.modules.profiles.data.model import REQUIRED_PROFILE_FIELDS
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError, ReportStateConflictError
from app.modules.reports.domain.repo import AcceptanceReportRepo, TemplateRepo
from app.modules.reports.helpers import DOCX_MIME, report_to_render_inputs
from app.modules.reports.storage import ObjectStorage


@dataclass(frozen=True)
class ApproveReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo
    storage: ObjectStorage
    render: Callable[..., bytes]
    template_repo: TemplateRepo
    email_service: Optional[EmailService] = None

    async def execute(self, *, report_id: str, approved_by: str) -> AcceptanceReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()
        if report.status != ReportStatus.REVIEWING:
            raise ReportStateConflictError("Only reviewing reports can be approved")

        snapshot = report.creator_snapshot
        if not all(str(snapshot.get(f, "")).strip() for f in REQUIRED_PROFILE_FIELDS):
            raise ReportStateConflictError("Creator profile is incomplete; cannot approve")

        line_item_images: dict[str, bytes] = {}
        for li in report.line_items:
            if li.article_image:
                try:
                    line_item_images[li.article_id] = await self.storage.get(li.article_image)
                except Exception:  # noqa: BLE001 — missing image is non-fatal
                    pass

        template_bytes = await self.template_repo.get_active_bytes()
        scalars, items = report_to_render_inputs(report)
        docx_bytes = self.render(
            scalars=scalars,
            line_items=items,
            template_bytes=template_bytes,
            line_item_images=line_item_images,
        )
        await self.storage.put(report.object_key, docx_bytes, content_type=DOCX_MIME)

        approved = await self.report_repo.approve(report_id, approved_by=approved_by)
        if approved is None:
            raise ReportNotFoundError()
        if self.email_service is not None:
            try:
                self.email_service.schedule_report_event(
                    event=ReportEmailEvent.APPROVED,
                    period=approved.period,
                    creator_user_id=approved.creator_user_id,
                )
            except Exception as exc:  # noqa: BLE001 - email is best-effort
                self.log_warning(
                    f"Failed to schedule approval email for report {approved.id}: {exc}"
                )
        return approved
