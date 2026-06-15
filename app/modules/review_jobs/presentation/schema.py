# app/modules/review_jobs/presentation/schema.py
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.review_jobs.data.model import ReviewCard, ReviewJob


class CreateReviewJobRequest(BaseModel):
    article_id: str = Field(..., min_length=1)
    workspace_id: str = Field(..., min_length=1)


class UpdateReviewJobRequest(BaseModel):
    """Exactly one action per PATCH: set total, append a result, or finalize."""
    total: Optional[int] = Field(default=None, ge=0)
    result: Optional[ReviewCard] = None
    status: Optional[str] = None  # "done" | "error"
    error: Optional[str] = None


class CreateReviewJobResponse(BaseModel):
    job_id: str


class ReviewCardResponse(BaseModel):
    kind: str
    source: str
    finding: str
    location_hint: str = ""

    @classmethod
    def from_card(cls, c: ReviewCard) -> "ReviewCardResponse":
        return cls(kind=c.kind, source=c.source, finding=c.finding, location_hint=c.location_hint)


class ReviewJobResponse(BaseModel):
    status: str
    progress: str
    completed: int
    total: Optional[int]
    results: list[ReviewCardResponse]
    error: Optional[str] = None

    @classmethod
    def from_job(cls, job: ReviewJob) -> "ReviewJobResponse":
        completed = len(job.results)
        total_str = str(job.total) if job.total is not None else "?"
        return cls(
            status=job.status.value,
            progress=f"{completed}/{total_str}",
            completed=completed,
            total=job.total,
            results=[ReviewCardResponse.from_card(c) for c in job.results],
            error=job.error,
        )
