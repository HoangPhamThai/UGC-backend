# app/modules/chat/domain/usecases/create_session.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.chat.data.model import ChatSession
from app.modules.chat.domain.repo import ChatSessionRepo


@dataclass(frozen=True)
class CreateSessionUseCase(LoggerMixin):
    repo: ChatSessionRepo

    async def execute(self, *, user_id: str, title: str = "") -> ChatSession:
        return await self.repo.create(ChatSession(user_id=user_id, title=title))
