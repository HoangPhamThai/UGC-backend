# app/modules/review_jobs/data/repo.py
from datetime import datetime, timezone
from typing import Optional, override

from pymongo import ASCENDING, ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.review_jobs.data.model import (
    ReviewCard,
    ReviewJob,
    ReviewJobStatus,
)
from app.modules.review_jobs.domain.repo import ReviewJobRepo


class ReviewJobDataRepository(LoggerMixin, ReviewJobRepo):
    def __init__(self) -> None:
        self.collection_name: str = ReviewJob.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("owner_user_id", ASCENDING)])

    @override
    async def create(self, job: ReviewJob) -> ReviewJob:
        coll = await self._get_collection()
        await coll.insert_one(job.model_dump(by_alias=True))
        return job

    @override
    async def get_by_id(self, job_id: str) -> Optional[ReviewJob]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": job_id})
        return ReviewJob.model_validate(doc) if doc else None

    @override
    async def set_total(self, job_id: str, total: int) -> Optional[ReviewJob]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": job_id},
            {"$set": {
                "total": total,
                "status": ReviewJobStatus.EVALUATING.value,
                "updated_at": datetime.now(timezone.utc),
            }},
            return_document=ReturnDocument.AFTER,
        )
        return ReviewJob.model_validate(doc) if doc else None

    @override
    async def append_result(self, job_id: str, card: ReviewCard) -> Optional[ReviewJob]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": job_id},
            {
                "$push": {"results": card.model_dump()},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )
        return ReviewJob.model_validate(doc) if doc else None

    @override
    async def finalize(
        self, job_id: str, status: ReviewJobStatus, *, error: Optional[str] = None
    ) -> Optional[ReviewJob]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": job_id},
            {"$set": {
                "status": status.value,
                "error": error,
                "updated_at": datetime.now(timezone.utc),
            }},
            return_document=ReturnDocument.AFTER,
        )
        return ReviewJob.model_validate(doc) if doc else None
