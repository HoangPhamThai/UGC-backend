from abc import ABC, abstractmethod
from typing import Optional

from app.modules.report_rule_jobs.data.model import RuleJob, RuleJobStatus


class RuleJobRepo(ABC):
    @abstractmethod
    async def create(self, job: RuleJob) -> RuleJob: ...
    @abstractmethod
    async def get_by_id(self, job_id: str) -> Optional[RuleJob]: ...
    @abstractmethod
    async def set_result(self, job_id: str, *, ir: dict, warnings: list[dict]) -> Optional[RuleJob]: ...
    @abstractmethod
    async def finalize(self, job_id: str, status: RuleJobStatus, *, error: Optional[str] = None) -> Optional[RuleJob]: ...
