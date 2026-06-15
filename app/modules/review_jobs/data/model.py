# app/modules/review_jobs/data/model.py
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.core.model import BaseMongoModel, make_prefixed_id


class ReviewJobStatus(str, Enum):
    PARSING = "parsing"
    EVALUATING = "evaluating"
    DONE = "done"
    ERROR = "error"


class ReviewCard(BaseModel):
    kind: str
    source: str
    finding: str
    location_hint: str = ""


class ReviewJob(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("rj"), alias="_id")
    article_id: str
    workspace_id: str
    owner_user_id: str
    status: ReviewJobStatus = ReviewJobStatus.PARSING
    total: Optional[int] = None
    results: list[ReviewCard] = Field(default_factory=list)
    error: Optional[str] = None

    class Config:
        collection_name = "review_jobs"
