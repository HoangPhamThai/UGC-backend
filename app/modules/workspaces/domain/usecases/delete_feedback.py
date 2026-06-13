# app/modules/workspaces/domain/usecases/delete_feedback.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import AWAITING_QC_STATUSES, FeedbackStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    FeedbackNotFoundError,
    FeedbackStateConflictError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, FeedbackRepo
from app.modules.workspaces.domain.usecases._review_guard import (
    ensure_claimed_by_caller,
    ensure_qc_scope,
)


@dataclass(frozen=True)
class DeleteFeedbackUseCase(LoggerMixin):
    article_repo: ArticleRepo
    feedback_repo: FeedbackRepo

    async def execute(
        self,
        *,
        workspace_id: str,
        article_id: str,
        feedback_id: str,
        caller: User,
    ) -> None:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        ensure_qc_scope(article, caller)
        if article.status not in AWAITING_QC_STATUSES:
            raise ArticleStateConflictError("Article is not awaiting review")
        ensure_claimed_by_caller(article, caller)

        feedback = await self.feedback_repo.get_by_id(feedback_id)
        if feedback is None or feedback.article_id != article_id:
            raise FeedbackNotFoundError()
        if feedback.status != FeedbackStatus.DRAFT:
            raise FeedbackStateConflictError("Only draft feedback can be deleted")
        if feedback.author_id != caller.id:
            raise FeedbackStateConflictError("Only the author can delete this feedback")

        deleted = await self.feedback_repo.delete(feedback_id)
        if not deleted:
            raise FeedbackNotFoundError()
