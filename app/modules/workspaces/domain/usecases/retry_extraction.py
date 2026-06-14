# app/modules/workspaces/domain/usecases/retry_extraction.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class RetryExtractionUseCase(LoggerMixin):
    """Re-queue metrics extraction for an article that already has a link
    (spec §6.2). Creator-owner scoped; blocked once a report locks the article."""

    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> Article:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        if article.report_id is not None:
            raise ArticleStateConflictError(
                "Article is locked by an acceptance report"
            )
        if not article.link:
            raise ArticleStateConflictError("Article has no link to extract")

        updated = await self.article_repo.set_extraction_pending(article_id)
        if updated is None:
            raise ArticleNotFoundError()
        return updated
