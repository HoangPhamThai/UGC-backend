# app/modules/chat/domain/repo.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.modules.chat.data.model import ChatMessage, ChatSession


@dataclass(frozen=True)
class ChatSessionSummary:
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ChatSessionRepo(ABC):
    @abstractmethod
    async def create(self, session: ChatSession) -> ChatSession: ...

    @abstractmethod
    async def get_by_id(self, session_id: str) -> Optional[ChatSession]: ...

    @abstractmethod
    async def list_summaries_by_owner(
        self, user_id: str, *, skip: int, limit: int
    ) -> list[ChatSessionSummary]: ...

    @abstractmethod
    async def count_by_owner(self, user_id: str) -> int: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...

    @abstractmethod
    async def append_messages(
        self, session_id: str, messages: list[ChatMessage], *, title: Optional[str]
    ) -> Optional[ChatSession]:
        """Push messages, bump updated_at; if title is not None, set it."""
        ...

    @abstractmethod
    async def clear_messages(self, session_id: str) -> Optional[ChatSession]:
        """Empty the messages array, bump updated_at."""
        ...
