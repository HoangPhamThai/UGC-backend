# app/modules/workspaces/domain/usecases/withdraw_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, ArticleEvent, ArticleEventType, ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    ClaimConflictError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleEventRepo, ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class WithdrawArticleUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo
    event_repo: ArticleEventRepo

    async def execute(self, *, workspace_id: str, article_id: str, caller: User) -> Article:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        if article.status != ArticleStatus.SUBMITTED:
            raise ArticleStateConflictError("Only a submitted article can be withdrawn")
        if article.claimed_by is not None:
            raise ClaimConflictError("A reviewer has already started; cannot withdraw")

        updated = await self.article_repo.update_status(
            article_id,
            status=ArticleStatus.NOT_SUBMITTED,
            last_activity_by=caller.id,
        )
        if updated is None:
            raise ArticleNotFoundError()
        await self.event_repo.create(
            ArticleEvent(article_id=article_id, actor_id=caller.id, type=ArticleEventType.WITHDRAWN)
        )
        self.log_info(f"Article withdrawn: id={article_id} by={caller.id}")
        return updated
