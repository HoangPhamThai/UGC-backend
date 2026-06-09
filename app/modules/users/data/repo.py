from typing import Optional, override

from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.users.domain.repo import UserRepo


class UserDataRepository(LoggerMixin, UserRepo):

    def __init__(self) -> None:
        self.collection_name: str = User.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    @override
    async def create(self, user: User) -> User:
        collection = await self._get_collection()
        payload = user.model_dump(by_alias=True)
        await collection.insert_one(payload)
        return user

    @override
    async def get_by_id(self, user_id: str) -> Optional[User]:
        collection = await self._get_collection()
        doc = await collection.find_one({"_id": user_id})
        return User.model_validate(doc) if doc else None

    @override
    async def get_by_email(self, email: str) -> Optional[User]:
        collection = await self._get_collection()
        doc = await collection.find_one({"email": email})
        return User.model_validate(doc) if doc else None

    @override
    async def update(self, user: User) -> User:
        collection = await self._get_collection()
        payload = user.model_dump(by_alias=True, exclude={"_id"})
        await collection.update_one({"_id": user.id}, {"$set": payload})
        return user

    @override
    async def exists_with_role(self, role: UserRole) -> bool:
        collection = await self._get_collection()
        doc = await collection.find_one(
            {"role": role.value}, projection={"_id": 1}
        )
        return doc is not None

    @override
    async def list_by_role(
        self, role: UserRole, *, skip: int = 0, limit: int = 50
    ) -> list[User]:
        collection = await self._get_collection()
        cursor = collection.find({"role": role.value}).skip(skip).limit(limit)
        docs = [doc async for doc in cursor]
        return [User.model_validate(doc) for doc in docs]

    @override
    async def count_by_role(self, role: UserRole) -> int:
        collection = await self._get_collection()
        return await collection.count_documents({"role": role.value})
