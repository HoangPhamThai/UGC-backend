from datetime import datetime, timezone
from typing import Optional, override

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.report_rule_jobs.data.model import RuleJob, RuleJobStatus
from app.modules.report_rule_jobs.domain.repo import RuleJobRepo


class RuleJobDataRepository(LoggerMixin, RuleJobRepo):
    def __init__(self) -> None:
        self.collection_name = RuleJob.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("owner_user_id", ASCENDING), ("created_at", DESCENDING)])

    @override
    async def create(self, job: RuleJob) -> RuleJob:
        coll = await self._get_collection()
        await coll.insert_one(job.model_dump(by_alias=True))
        return job

    @override
    async def get_by_id(self, job_id: str) -> Optional[RuleJob]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": job_id})
        return RuleJob.model_validate(doc) if doc else None

    @override
    async def set_result(self, job_id: str, *, ir: dict, warnings: list[dict]) -> Optional[RuleJob]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": job_id},
            {"$set": {"ir": ir, "warnings": warnings,
                      "status": RuleJobStatus.RUNNING.value,
                      "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        return RuleJob.model_validate(doc) if doc else None

    @override
    async def finalize(self, job_id, status, *, error=None) -> Optional[RuleJob]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": job_id},
            {"$set": {"status": status.value, "error": error,
                      "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        return RuleJob.model_validate(doc) if doc else None
