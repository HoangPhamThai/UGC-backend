# app/modules/review_jobs/domain/usecases/update_job.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.review_jobs.data.model import ReviewCard, ReviewJob, ReviewJobStatus
from app.modules.review_jobs.domain.errors import ReviewJobNotFoundError
from app.modules.review_jobs.domain.repo import ReviewJobRepo


@dataclass(frozen=True)
class SetTotalUseCase(LoggerMixin):
    repo: ReviewJobRepo

    async def execute(self, *, job_id: str, total: int) -> ReviewJob:
        job = await self.repo.set_total(job_id, total)
        if job is None:
            raise ReviewJobNotFoundError()
        return job


@dataclass(frozen=True)
class AppendResultUseCase(LoggerMixin):
    repo: ReviewJobRepo

    async def execute(self, *, job_id: str, card: ReviewCard) -> ReviewJob:
        job = await self.repo.append_result(job_id, card)
        if job is None:
            raise ReviewJobNotFoundError()
        return job


@dataclass(frozen=True)
class FinalizeJobUseCase(LoggerMixin):
    repo: ReviewJobRepo

    async def execute(
        self, *, job_id: str, status: ReviewJobStatus, error: Optional[str] = None
    ) -> ReviewJob:
        job = await self.repo.finalize(job_id, status, error=error)
        if job is None:
            raise ReviewJobNotFoundError()
        return job
