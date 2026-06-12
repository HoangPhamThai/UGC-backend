# app/modules/workspaces/domain/usecases/submit_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import (
    Article,
    ArticleEvent,
    ArticleEventType,
    ArticleStatus,
)
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleEventRepo, ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class SubmitArticleUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo
    event_repo: ArticleEventRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> Article:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        if article.status == ArticleStatus.NOT_SUBMITTED:
            target = ArticleStatus.SUBMITTED
            event_type = ArticleEventType.SUBMITTED
        elif article.status == ArticleStatus.FEEDBACK_PROVIDED:
            target = ArticleStatus.EDITED
            event_type = ArticleEventType.EDITED_RESUBMITTED
        else:
            raise ArticleStateConflictError("Article is not in a submittable state")

        updated = await self.article_repo.update_status(
            article_id, status=target, last_activity_by=caller.id
        )
        if updated is None:
            raise ArticleNotFoundError()
        await self.event_repo.create(
            ArticleEvent(article_id=article_id, actor_id=caller.id, type=event_type)
        )
        self.log_info(f"Article submitted: id={article_id} status={target.value}")
        return updated
