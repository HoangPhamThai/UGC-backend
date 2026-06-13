# app/modules/chat/domain/usecases/list_messages.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.chat.data.model import ChatMessage
from app.modules.chat.domain.errors import ChatSessionNotFoundError
from app.modules.chat.domain.repo import ChatSessionRepo


@dataclass(frozen=True)
class ListMessagesUseCase(LoggerMixin):
    repo: ChatSessionRepo

    async def execute(
        self, *, session_id: str, caller_id: str, limit: Optional[int]
    ) -> list[ChatMessage]:
        session = await self.repo.get_by_id(session_id)
        if session is None or session.user_id != caller_id:
            raise ChatSessionNotFoundError()
        if limit is not None and limit >= 0:
            return session.messages[-limit:] if limit else []
        return list(session.messages)
