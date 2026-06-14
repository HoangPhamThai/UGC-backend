from typing import Optional, override

from pymongo import ASCENDING
from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.profiles.data.model import CreatorProfile
from app.modules.profiles.domain.repo import CreatorProfileRepo


class CreatorProfileDataRepository(LoggerMixin, CreatorProfileRepo):

    def __init__(self) -> None:
        self.collection_name: str = CreatorProfile.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("user_id", ASCENDING)], unique=True)

    @override
    async def get_by_user_id(self, user_id: str) -> Optional[CreatorProfile]:
        coll = await self._get_collection()
        doc = await coll.find_one({"user_id": user_id})
        return CreatorProfile.model_validate(doc) if doc else None

    @override
    async def upsert(self, profile: CreatorProfile) -> CreatorProfile:
        coll = await self._get_collection()
        payload = profile.model_dump(by_alias=True)
        await coll.update_one(
            {"user_id": profile.user_id}, {"$set": payload}, upsert=True
        )
        return profile
