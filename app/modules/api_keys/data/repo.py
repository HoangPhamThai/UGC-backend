from typing import Optional, override

from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.api_keys.data.model import ApiKey
from app.modules.api_keys.domain.repo import ApiKeyRepo


class ApiKeyDataRepository(LoggerMixin, ApiKeyRepo):

    def __init__(self) -> None:
        self.collection_name: str = ApiKey.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    @override
    async def create(self, api_key: ApiKey) -> ApiKey:
        collection = await self._get_collection()
        payload = api_key.model_dump(by_alias=True)
        await collection.insert_one(payload)
        return api_key

    @override
    async def get_by_key_hash(self, key_hash: str) -> Optional[ApiKey]:
        collection = await self._get_collection()
        doc = await collection.find_one({"key_hash": key_hash})
        return ApiKey.model_validate(doc) if doc else None

    @override
    async def list_by_user_id(self, user_id: str) -> list[ApiKey]:
        collection = await self._get_collection()
        cursor = collection.find({"user_id": user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=1000)
        return [ApiKey.model_validate(d) for d in docs]

    @override
    async def delete(self, key_id: str) -> bool:
        collection = await self._get_collection()
        result = await collection.delete_one({"_id": key_id})
        return result.deleted_count > 0
