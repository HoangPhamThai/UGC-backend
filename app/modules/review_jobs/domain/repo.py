# app/modules/review_jobs/domain/repo.py
from abc import ABC, abstractmethod
from typing import Optional

from app.modules.review_jobs.data.model import (
    ReviewCard,
    ReviewJob,
    ReviewJobStatus,
)


class ReviewJobRepo(ABC):
    @abstractmethod
    async def create(self, job: ReviewJob) -> ReviewJob: ...

    @abstractmethod
    async def get_by_id(self, job_id: str) -> Optional[ReviewJob]: ...

    @abstractmethod
    async def set_total(self, job_id: str, total: int) -> Optional[ReviewJob]:
        """Set total and flip status to EVALUATING; bump updated_at."""
        ...

    @abstractmethod
    async def append_result(self, job_id: str, card: ReviewCard) -> Optional[ReviewJob]:
        """Atomically push one card; bump updated_at."""
        ...

    @abstractmethod
    async def finalize(
        self, job_id: str, status: ReviewJobStatus, *, error: Optional[str] = None
    ) -> Optional[ReviewJob]:
        """Set terminal status (DONE/ERROR) and optional error; bump updated_at."""
        ...
