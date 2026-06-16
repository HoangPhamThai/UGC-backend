from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.report_rule_jobs.data.model import RuleJob, RuleJobStatus
from app.modules.report_rule_jobs.domain.errors import RuleJobNotFoundError
from app.modules.report_rule_jobs.domain.repo import RuleJobRepo


@dataclass(frozen=True)
class SetResultUseCase(LoggerMixin):
    repo: RuleJobRepo

    async def execute(self, *, job_id: str, ir: dict, warnings: list[dict]) -> RuleJob:
        job = await self.repo.set_result(job_id, ir=ir, warnings=warnings)
        if job is None:
            raise RuleJobNotFoundError()
        return job


@dataclass(frozen=True)
class FinalizeRuleJobUseCase(LoggerMixin):
    repo: RuleJobRepo

    async def execute(self, *, job_id: str, status: RuleJobStatus, error: Optional[str] = None) -> RuleJob:
        job = await self.repo.finalize(job_id, status, error=error)
        if job is None:
            raise RuleJobNotFoundError()
        return job
