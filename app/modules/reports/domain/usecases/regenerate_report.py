# app/modules/reports/domain/usecases/regenerate_report.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError, ReportStateConflictError
from app.modules.reports.domain.repo import AcceptanceReportRepo
from app.modules.reports.domain.usecases.delete_report import DeleteReportUseCase
from app.modules.reports.domain.usecases.generate_reports import GenerateReportsUseCase


@dataclass(frozen=True)
class RegenerateReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo
    delete_uc: DeleteReportUseCase
    generate_uc: GenerateReportsUseCase

    async def execute(self, *, report_id: str, regenerated_by: str) -> AcceptanceReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()
        if report.status != ReportStatus.DRAFT:
            raise ReportStateConflictError("Only a draft report can be regenerated")

        price = report.article_award_price
        # Recover the tax rate from the stored draft (tax = round(total_award * rate)).
        tax_rate = (report.tax / report.total_award) if report.total_award else 0.0
        creator = report.creator_user_id
        period = report.period

        # Delete first (unlocks articles + frees the unique (creator, period) slot),
        # then regenerate from current data. The unique index forbids two reports for
        # the same (creator, period), so delete-before-generate is required.
        await self.delete_uc.execute(report_id=report_id)
        created = await self.generate_uc.execute(
            period=period, article_award_price=price, tax_rate=tax_rate,
            created_by=regenerated_by, creator_user_id=creator,
        )
        if not created:
            raise ReportStateConflictError(
                "No eligible articles remain to regenerate this report"
            )
        return created[0]
