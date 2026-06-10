# app/modules/workspaces/domain/usecases/delete_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class DeleteArticleUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> None:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        # Rejected is a frozen terminal state — no edit/delete/review (article.md §4.2).
        if article.status == ArticleStatus.REJECTED:
            raise ArticleStateConflictError("Rejected articles cannot be deleted")

        await self.article_repo.delete(article_id)
        await self.workspace_repo.increment_article_count(workspace_id, by=-1)
        self.log_info(f"Article deleted: id={article_id} ws={workspace_id}")
