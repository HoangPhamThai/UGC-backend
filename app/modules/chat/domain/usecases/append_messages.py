# app/modules/chat/domain/usecases/append_messages.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.chat.data.model import ChatMessage, ChatRole, ChatSession
from app.modules.chat.domain.errors import ChatSessionNotFoundError
from app.modules.chat.domain.repo import ChatSessionRepo

_TITLE_MAX = 80


@dataclass(frozen=True)
class AppendMessagesUseCase(LoggerMixin):
    repo: ChatSessionRepo

    async def execute(
        self, *, session_id: str, caller_id: str, messages: list[ChatMessage]
    ) -> ChatSession:
        session = await self.repo.get_by_id(session_id)
        if session is None or session.user_id != caller_id:
            raise ChatSessionNotFoundError()

        title = None
        if not session.title:
            first_user = next((m for m in messages if m.role == ChatRole.USER), None)
            if first_user is not None:
                title = first_user.content[:_TITLE_MAX]

        updated = await self.repo.append_messages(session_id, messages, title=title)
        if updated is None:
            raise ChatSessionNotFoundError()
        return updated
