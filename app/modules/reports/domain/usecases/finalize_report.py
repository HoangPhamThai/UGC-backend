# app/modules/reports/domain/usecases/finalize_report.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.profiles.data.model import REQUIRED_PROFILE_FIELDS
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError, ReportStateConflictError
from app.modules.reports.domain.repo import AcceptanceReportRepo


@dataclass(frozen=True)
class FinalizeReportUseCase(LoggerMixin):
    report_repo: AcceptanceReportRepo

    async def execute(self, *, report_id: str, finalized_by: str) -> AcceptanceReport:
        report = await self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()
        if report.status != ReportStatus.DRAFT:
            raise ReportStateConflictError("Only a draft report can be finalized")

        snapshot = report.creator_snapshot
        if not all(str(snapshot.get(f, "")).strip() for f in REQUIRED_PROFILE_FIELDS):
            raise ReportStateConflictError(
                "Creator profile is incomplete; cannot finalize"
            )

        finalized = await self.report_repo.finalize(report_id, finalized_by=finalized_by)
        if finalized is None:
            raise ReportNotFoundError()
        return finalized
