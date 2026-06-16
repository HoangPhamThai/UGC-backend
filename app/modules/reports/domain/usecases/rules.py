from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.domain.errors import ReportValidationError
from app.modules.reports.domain.repo import ReportRulesRepo
from app.modules.reports.rules.validator import validate_ir

_EMPTY_IR = {"version": 1, "rules": []}


@dataclass(frozen=True)
class GetRulesUseCase(LoggerMixin):
    rules_repo: ReportRulesRepo

    async def execute(self) -> dict:
        doc = await self.rules_repo.get_active()
        if doc is None:
            return {"source_markdown": "", "ir": _EMPTY_IR, "warnings": [], "status": "empty"}
        return {
            "source_markdown": doc.get("source_markdown", ""),
            "ir": doc.get("ir", _EMPTY_IR),
            "warnings": doc.get("warnings", []),
            "status": doc.get("status", "ok"),
        }


@dataclass(frozen=True)
class SaveRulesUseCase(LoggerMixin):
    rules_repo: ReportRulesRepo

    async def execute(self, *, source_markdown: str, ir: dict, updated_by: str) -> dict:
        errors = validate_ir(ir)
        if errors:
            raise ReportValidationError("IR không hợp lệ: " + "; ".join(errors))
        status = "ok"
        return await self.rules_repo.save_active(
            source_markdown=source_markdown, ir=ir, warnings=[],
            status=status, updated_by=updated_by,
        )
