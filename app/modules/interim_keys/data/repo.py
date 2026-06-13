# app/modules/interim_keys/data/repo.py
from datetime import datetime
from typing import Optional, override

from pymongo import ASCENDING
from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.interim_keys.data.model import InterimKey
from app.modules.interim_keys.domain.repo import InterimKeyRepo


class InterimKeyDataRepository(LoggerMixin, InterimKeyRepo):
    def __init__(self) -> None:
        self.collection_name: str = InterimKey.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("key_hash", ASCENDING)], unique=True)
        # Mongo auto-purges expired keys (purge lags up to ~60s; on-use check still applies).
        await coll.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)

    @override
    async def create(self, key: InterimKey) -> InterimKey:
        coll = await self._get_collection()
        await coll.insert_one(key.model_dump(by_alias=True))
        return key

    @override
    async def get_active_by_hash(
        self, key_hash: str, now: datetime
    ) -> Optional[InterimKey]:
        coll = await self._get_collection()
        doc = await coll.find_one({"key_hash": key_hash, "expires_at": {"$gt": now}})
        return InterimKey.model_validate(doc) if doc else None

    @override
    async def delete_by_hash(self, key_hash: str) -> bool:
        coll = await self._get_collection()
        result = await coll.delete_one({"key_hash": key_hash})
        return result.deleted_count > 0
