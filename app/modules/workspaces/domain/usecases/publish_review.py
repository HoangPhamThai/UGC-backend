# app/modules/workspaces/domain/usecases/publish_review.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import (
    AWAITING_QC_STATUSES,
    Article,
    ArticleEvent,
    ArticleEventType,
    ArticleStatus,
)
from app.modules.workspaces.domain.errors import ArticleNotFoundError, ArticleStateConflictError
from app.modules.workspaces.domain.repo import ArticleEventRepo, ArticleRepo, FeedbackRepo
from app.modules.workspaces.domain.usecases._review_guard import (
    ensure_claimed_by_caller,
    ensure_qc_scope,
)


@dataclass(frozen=True)
class PublishReviewUseCase(LoggerMixin):
    article_repo: ArticleRepo
    feedback_repo: FeedbackRepo
    event_repo: ArticleEventRepo

    async def execute(self, *, workspace_id: str, article_id: str, caller: User) -> Article:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        ensure_qc_scope(article, caller)
        if article.status not in AWAITING_QC_STATUSES:
            raise ArticleStateConflictError("Article is not awaiting review")
        ensure_claimed_by_caller(article, caller)

        # Promote this session's drafts, then verify something is actually blocking.
        await self.feedback_repo.mark_drafts_open(article_id)
        open_count = await self.feedback_repo.count_open(article_id)
        if open_count == 0:
            raise ArticleStateConflictError(
                "No open feedback to send back; approve or add feedback first"
            )

        updated = await self.article_repo.update_status(
            article_id,
            status=ArticleStatus.FEEDBACK_PROVIDED,
            reviewer_user_id=caller.id,
            set_reviewed_at=True,
            last_activity_by=caller.id,
            increment_review_round=True,
        )
        if updated is None:
            raise ArticleNotFoundError()
        await self.event_repo.create(
            ArticleEvent(
                article_id=article_id, actor_id=caller.id,
                type=ArticleEventType.REVIEW_PUBLISHED,
                payload={"open_count": open_count, "round": updated.review_round},
            )
        )
        self.log_info(f"Review published: article={article_id} open={open_count}")
        return updated
