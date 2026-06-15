# app/modules/review_jobs/domain/usecases/get_latest_job.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.review_jobs.data.model import ReviewJob
from app.modules.review_jobs.domain.repo import ReviewJobRepo


@dataclass(frozen=True)
class GetLatestReviewJobUseCase(LoggerMixin):
    repo: ReviewJobRepo

    async def execute(self, *, caller_id: str, article_id: str) -> Optional[ReviewJob]:
        return await self.repo.get_latest_for_article(caller_id, article_id)
