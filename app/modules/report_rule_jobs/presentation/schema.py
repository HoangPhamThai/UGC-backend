from typing import Optional

from pydantic import BaseModel, Field

from app.modules.report_rule_jobs.data.model import RuleJob


class CreateRuleJobRequest(BaseModel):
    source_markdown: str = Field(..., min_length=1)


class UpdateRuleJobRequest(BaseModel):
    """One action per PATCH: set result (ir+warnings) OR finalize (status[, error])."""
    ir: Optional[dict] = None
    warnings: Optional[list[dict]] = None
    status: Optional[str] = None
    error: Optional[str] = None


class CreateRuleJobResponse(BaseModel):
    job_id: str


class RuleJobResponse(BaseModel):
    status: str
    ir: Optional[dict] = None
    warnings: list[dict] = []
    error: Optional[str] = None

    @classmethod
    def from_job(cls, job: RuleJob) -> "RuleJobResponse":
        return cls(status=job.status.value, ir=job.ir, warnings=job.warnings, error=job.error)
