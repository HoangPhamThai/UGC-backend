# app/modules/chat/domain/usecases/clear_messages.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.chat.data.model import ChatSession
from app.modules.chat.domain.errors import ChatSessionNotFoundError
from app.modules.chat.domain.repo import ChatSessionRepo


@dataclass(frozen=True)
class ClearMessagesUseCase(LoggerMixin):
    repo: ChatSessionRepo

    async def execute(self, *, session_id: str, caller_id: str) -> ChatSession:
        session = await self.repo.get_by_id(session_id)
        if session is None or session.user_id != caller_id:
            raise ChatSessionNotFoundError()
        updated = await self.repo.clear_messages(session_id)
        if updated is None:
            raise ChatSessionNotFoundError()
        return updated
