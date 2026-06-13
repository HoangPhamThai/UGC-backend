# app/modules/chat/domain/usecases/list_sessions.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.chat.domain.repo import ChatSessionRepo, ChatSessionSummary


@dataclass(frozen=True)
class ListSessionsUseCase(LoggerMixin):
    repo: ChatSessionRepo

    async def execute(
        self, *, user_id: str, page: int, limit: int
    ) -> tuple[list[ChatSessionSummary], int]:
        skip = (page - 1) * limit
        items = await self.repo.list_summaries_by_owner(user_id, skip=skip, limit=limit)
        total = await self.repo.count_by_owner(user_id)
        return items, total
