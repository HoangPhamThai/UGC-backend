# app/modules/chat/domain/usecases/delete_session.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.chat.domain.errors import ChatSessionNotFoundError
from app.modules.chat.domain.repo import ChatSessionRepo


@dataclass(frozen=True)
class DeleteSessionUseCase(LoggerMixin):
    repo: ChatSessionRepo

    async def execute(self, *, session_id: str, caller_id: str) -> None:
        session = await self.repo.get_by_id(session_id)
        if session is None or session.user_id != caller_id:
            raise ChatSessionNotFoundError()
        await self.repo.delete(session_id)
