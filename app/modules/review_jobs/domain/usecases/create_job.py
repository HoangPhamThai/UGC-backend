# app/modules/review_jobs/domain/usecases/create_job.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.review_jobs.data.model import ReviewJob
from app.modules.review_jobs.domain.repo import ReviewJobRepo


@dataclass(frozen=True)
class CreateReviewJobUseCase(LoggerMixin):
    repo: ReviewJobRepo

    async def execute(self, *, owner_user_id: str, article_id: str, workspace_id: str) -> ReviewJob:
        job = ReviewJob(
            owner_user_id=owner_user_id, article_id=article_id, workspace_id=workspace_id
        )
        await self.repo.create(job)
        self.log_info(f"Review job created id={job.id} owner={owner_user_id}")
        return job
