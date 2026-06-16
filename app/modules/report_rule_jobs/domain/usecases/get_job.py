from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.report_rule_jobs.data.model import RuleJob
from app.modules.report_rule_jobs.domain.errors import RuleJobNotFoundError
from app.modules.report_rule_jobs.domain.repo import RuleJobRepo


@dataclass(frozen=True)
class GetRuleJobUseCase(LoggerMixin):
    repo: RuleJobRepo

    async def execute(self, *, job_id: str, caller_id: str) -> RuleJob:
        job = await self.repo.get_by_id(job_id)
        if job is None or job.owner_user_id != caller_id:
            raise RuleJobNotFoundError()
        return job
