# app/modules/review_jobs/domain/usecases/get_job.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.review_jobs.data.model import ReviewJob
from app.modules.review_jobs.domain.errors import ReviewJobNotFoundError
from app.modules.review_jobs.domain.repo import ReviewJobRepo


@dataclass(frozen=True)
class GetReviewJobUseCase(LoggerMixin):
    repo: ReviewJobRepo

    async def execute(self, *, job_id: str, caller_id: str) -> ReviewJob:
        job = await self.repo.get_by_id(job_id)
        if job is None or job.owner_user_id != caller_id:
            raise ReviewJobNotFoundError()
        return job
