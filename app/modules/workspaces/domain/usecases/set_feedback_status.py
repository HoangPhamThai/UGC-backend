# app/modules/workspaces/domain/usecases/set_feedback_status.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import (
    AWAITING_QC_STATUSES,
    ArticleEvent,
    ArticleEventType,
    Feedback,
    FeedbackStatus,
)
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    FeedbackNotFoundError,
    FeedbackStateConflictError,
)
from app.modules.workspaces.domain.repo import ArticleEventRepo, ArticleRepo, FeedbackRepo
from app.modules.workspaces.domain.usecases._review_guard import (
    ensure_claimed_by_caller,
    ensure_qc_scope,
)

# (from_status, target) -> event type. Defines the legal transitions.
_ALLOWED: dict[tuple[FeedbackStatus, FeedbackStatus], ArticleEventType] = {
    (FeedbackStatus.OPEN, FeedbackStatus.RESOLVED): ArticleEventType.FEEDBACK_RESOLVED,
    (FeedbackStatus.OPEN, FeedbackStatus.DISMISSED): ArticleEventType.FEEDBACK_DISMISSED,
    (FeedbackStatus.RESOLVED, FeedbackStatus.OPEN): ArticleEventType.FEEDBACK_REOPENED,
    (FeedbackStatus.DISMISSED, FeedbackStatus.OPEN): ArticleEventType.FEEDBACK_REOPENED,
}


@dataclass(frozen=True)
class SetFeedbackStatusUseCase(LoggerMixin):
    article_repo: ArticleRepo
    feedback_repo: FeedbackRepo
    event_repo: ArticleEventRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, feedback_id: str,
        target: FeedbackStatus, caller: User,
    ) -> Feedback:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        ensure_qc_scope(article, caller)
        ensure_claimed_by_caller(article, caller)

        if article.status not in AWAITING_QC_STATUSES:
            raise ArticleStateConflictError(
                "Feedback status can only be changed during an active review session"
            )

        feedback = await self.feedback_repo.get_by_id(feedback_id)
        if feedback is None or feedback.article_id != article_id:
            raise FeedbackNotFoundError()

        event_type = _ALLOWED.get((feedback.status, target))
        if event_type is None:
            raise FeedbackStateConflictError(
                f"Cannot move feedback from {feedback.status.value} to {target.value}"
            )

        is_reopen = target == FeedbackStatus.OPEN
        updated = await self.feedback_repo.set_status(
            feedback_id,
            status=target,
            resolved_by=caller.id if target == FeedbackStatus.RESOLVED else None,
            set_resolved_at=target == FeedbackStatus.RESOLVED,
            clear_resolved=is_reopen,
        )
        if updated is None:
            raise FeedbackNotFoundError()

        await self.article_repo.touch_activity(article_id, actor_id=caller.id)
        await self.event_repo.create(
            ArticleEvent(
                article_id=article_id, actor_id=caller.id, type=event_type,
                payload={"feedback_id": feedback_id},
            )
        )
        self.log_info(f"Feedback {event_type.value}: id={feedback_id}")
        return updated
