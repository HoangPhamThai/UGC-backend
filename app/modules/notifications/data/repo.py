# app/modules/notifications/data/repo.py
from datetime import datetime, timezone
from typing import Optional, override

from pymongo import DESCENDING, ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.notifications.data.model import Notification
from app.modules.notifications.domain.repo import NotificationRepo


class NotificationDataRepository(LoggerMixin, NotificationRepo):
    def __init__(self) -> None:
        self.collection_name: str = Notification.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("recipient_id", 1), ("created_at", DESCENDING)])
        await coll.create_index([("recipient_id", 1), ("read_at", 1)])

    @override
    async def create(self, notification: Notification) -> Notification:
        coll = await self._get_collection()
        await coll.insert_one(notification.model_dump(by_alias=True))
        return notification

    def _filter(self, recipient_id: str, unread_only: bool) -> dict:
        filt: dict = {"recipient_id": recipient_id}
        if unread_only:
            filt["read_at"] = None
        return filt

    @override
    async def list_for_recipient(
        self, recipient_id: str, *, unread_only: bool, skip: int, limit: int
    ) -> list[Notification]:
        coll = await self._get_collection()
        cursor = (
            coll.find(self._filter(recipient_id, unread_only))
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        docs = [doc async for doc in cursor]
        return [Notification.model_validate(d) for d in docs]

    @override
    async def count_for_recipient(self, recipient_id: str, *, unread_only: bool) -> int:
        coll = await self._get_collection()
        return await coll.count_documents(self._filter(recipient_id, unread_only))

    @override
    async def mark_read(self, notification_id: str, recipient_id: str) -> Optional[Notification]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": notification_id, "recipient_id": recipient_id, "read_at": None},
            {"$set": {"read_at": now, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if doc is not None:
            return Notification.model_validate(doc)
        # Already read or not owned: return the doc if it exists & is owned (idempotent), else None.
        existing = await coll.find_one({"_id": notification_id, "recipient_id": recipient_id})
        return Notification.model_validate(existing) if existing else None

    @override
    async def mark_all_read(self, recipient_id: str) -> int:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        result = await coll.update_many(
            {"recipient_id": recipient_id, "read_at": None},
            {"$set": {"read_at": now, "updated_at": now}},
        )
        return result.modified_count
