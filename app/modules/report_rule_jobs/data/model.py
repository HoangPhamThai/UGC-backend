from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class RuleJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    TIMEOUT = "timeout"


class RuleJob(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("rrj"), alias="_id")
    owner_user_id: str
    source_markdown: str = ""
    status: RuleJobStatus = RuleJobStatus.QUEUED
    ir: Optional[dict] = None
    warnings: list[dict] = Field(default_factory=list)
    error: Optional[str] = None

    class Config:
        collection_name = "report_rule_jobs"
