# app/modules/workspaces/domain/usecases/list_feedbacks.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import Feedback, FeedbackStatus
from app.modules.workspaces.domain.errors import ArticleNotFoundError
from app.modules.workspaces.domain.repo import ArticleRepo, FeedbackRepo, WorkspaceRepo
from app.modules.workspaces.domain.usecases._review_guard import ensure_qc_scope


@dataclass(frozen=True)
class ListFeedbacksUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo
    feedback_repo: FeedbackRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> list[Feedback]:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        is_qc = caller.role in (UserRole.QC, UserRole.SUPERUSER)
        if is_qc:
            ensure_qc_scope(article, caller)
        else:
            ws = await self.workspace_repo.get_by_id(workspace_id)
            if ws is None or ws.owner_user_id != caller.id:
                raise ArticleNotFoundError()

        feedbacks = await self.feedback_repo.list_by_article(article_id)
        # DRAFT feedback is visible only to its author (the composing QC).
        # SUPERUSER sees all drafts — consistent with every other guard.
        return [
            f for f in feedbacks
            if f.status != FeedbackStatus.DRAFT
            or (is_qc and (caller.role == UserRole.SUPERUSER or f.author_id == caller.id))
        ]
