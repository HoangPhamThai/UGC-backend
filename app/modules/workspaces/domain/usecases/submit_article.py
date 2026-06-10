# app/modules/workspaces/domain/usecases/submit_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class SubmitArticleUseCase(LoggerMixin):
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

        # Creator transitions (single "Submit for Review" button), article.md §4.2:
        #   not_submitted     -> submitted   (first review)
        #   feedback_provided -> edited       (resubmit after feedback)
        if article.status == ArticleStatus.NOT_SUBMITTED:
            target = ArticleStatus.SUBMITTED
        elif article.status == ArticleStatus.FEEDBACK_PROVIDED:
            target = ArticleStatus.EDITED
        else:
            raise ArticleStateConflictError(
                "Article is not in a submittable state"
            )

        updated = await self.article_repo.update_status(article_id, status=target)
        if updated is None:
            raise ArticleNotFoundError()
        self.log_info(f"Article submitted: id={article_id} status={target.value}")
        return updated
