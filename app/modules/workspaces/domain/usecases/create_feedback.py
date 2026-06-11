# app/modules/workspaces/domain/usecases/create_feedback.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import (
    AWAITING_QC_STATUSES,
    Feedback,
    FeedbackAnchor,
    FeedbackStatus,
)
from app.modules.workspaces.domain.errors import ArticleNotFoundError, ArticleStateConflictError
from app.modules.workspaces.domain.repo import ArticleRepo, FeedbackRepo
from app.modules.workspaces.domain.usecases._review_guard import (
    ensure_claimed_by_caller,
    ensure_qc_scope,
)


@dataclass(frozen=True)
class CreateFeedbackUseCase(LoggerMixin):
    article_repo: ArticleRepo
    feedback_repo: FeedbackRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User,
        body: str, anchor: FeedbackAnchor,
    ) -> Feedback:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        ensure_qc_scope(article, caller)
        if article.status not in AWAITING_QC_STATUSES:
            raise ArticleStateConflictError("Article is not awaiting review")
        ensure_claimed_by_caller(article, caller)

        feedback = Feedback(
            article_id=article_id, author_id=caller.id, body=body,
            status=FeedbackStatus.DRAFT, anchor=anchor,
        )
        created = await self.feedback_repo.create(feedback)
        self.log_info(f"Feedback draft created: id={created.id} article={article_id}")
        return created
