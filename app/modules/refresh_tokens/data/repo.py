from typing import Optional, override

from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.refresh_tokens.data.model import RefreshToken
from app.modules.refresh_tokens.domain.repo import RefreshTokenRepo


class RefreshTokenDataRepository(LoggerMixin, RefreshTokenRepo):

    def __init__(self) -> None:
        self.collection_name: str = RefreshToken.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    @override
    async def create(self, token: RefreshToken) -> RefreshToken:
        collection = await self._get_collection()
        payload = token.model_dump(by_alias=True)
        await collection.insert_one(payload)
        return token

    @override
    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        collection = await self._get_collection()
        doc = await collection.find_one({"token_hash": token_hash})
        return RefreshToken.model_validate(doc) if doc else None

    @override
    async def delete_all_by_user_id(self, user_id: str) -> int:
        collection = await self._get_collection()
        result = await collection.delete_many({"user_id": user_id})
        return result.deleted_count
