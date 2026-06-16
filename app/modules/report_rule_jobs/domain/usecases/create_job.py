from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.report_rule_jobs.data.model import RuleJob
from app.modules.report_rule_jobs.domain.repo import RuleJobRepo


@dataclass(frozen=True)
class CreateRuleJobUseCase(LoggerMixin):
    repo: RuleJobRepo

    async def execute(self, *, owner_user_id: str, source_markdown: str) -> RuleJob:
        job = RuleJob(owner_user_id=owner_user_id, source_markdown=source_markdown)
        await self.repo.create(job)
        self.log_info(f"Rule job created id={job.id} owner={owner_user_id}")
        return job
