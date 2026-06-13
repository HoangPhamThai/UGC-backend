# app/modules/chat/data/repo.py
from datetime import datetime, timezone
from typing import Optional, override

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.chat.data.model import ChatMessage, ChatSession
from app.modules.chat.domain.repo import ChatSessionRepo, ChatSessionSummary


class ChatSessionDataRepository(LoggerMixin, ChatSessionRepo):
    def __init__(self) -> None:
        self.collection_name: str = ChatSession.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("user_id", ASCENDING)])

    @override
    async def create(self, session: ChatSession) -> ChatSession:
        coll = await self._get_collection()
        await coll.insert_one(session.model_dump(by_alias=True))
        return session

    @override
    async def get_by_id(self, session_id: str) -> Optional[ChatSession]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": session_id})
        return ChatSession.model_validate(doc) if doc else None

    @override
    async def list_summaries_by_owner(
        self, user_id: str, *, skip: int, limit: int
    ) -> list[ChatSessionSummary]:
        coll = await self._get_collection()
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"updated_at": DESCENDING}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$project": {
                    "title": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "message_count": {"$size": {"$ifNull": ["$messages", []]}},
                }
            },
        ]
        out: list[ChatSessionSummary] = []
        cursor = await coll.aggregate(pipeline)
        async for doc in cursor:
            out.append(
                ChatSessionSummary(
                    id=doc["_id"],
                    title=doc.get("title", ""),
                    message_count=doc.get("message_count", 0),
                    created_at=doc["created_at"],
                    updated_at=doc["updated_at"],
                )
            )
        return out

    @override
    async def count_by_owner(self, user_id: str) -> int:
        coll = await self._get_collection()
        return await coll.count_documents({"user_id": user_id})

    @override
    async def delete(self, session_id: str) -> None:
        coll = await self._get_collection()
        await coll.delete_one({"_id": session_id})

    @override
    async def append_messages(
        self, session_id: str, messages: list[ChatMessage], *, title: Optional[str]
    ) -> Optional[ChatSession]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        set_fields: dict = {"updated_at": now}
        if title is not None:
            set_fields["title"] = title
        doc = await coll.find_one_and_update(
            {"_id": session_id},
            {
                "$push": {"messages": {"$each": [m.model_dump() for m in messages]}},
                "$set": set_fields,
            },
            return_document=ReturnDocument.AFTER,
        )
        return ChatSession.model_validate(doc) if doc else None

    @override
    async def clear_messages(self, session_id: str) -> Optional[ChatSession]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": session_id},
            {"$set": {"messages": [], "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        return ChatSession.model_validate(doc) if doc else None
