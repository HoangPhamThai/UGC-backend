# app/modules/workspaces/domain/usecases/approve_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import (
    AWAITING_QC_STATUSES,
    Article,
    ArticleEvent,
    ArticleEventType,
    ArticleStatus,
    FeedbackStatus,
)
from app.modules.workspaces.domain.errors import ArticleNotFoundError, ArticleStateConflictError
from app.modules.workspaces.domain.repo import ArticleEventRepo, ArticleRepo, FeedbackRepo
from app.modules.workspaces.domain.usecases._review_guard import (
    ensure_claimed_by_caller,
    ensure_qc_scope,
)


@dataclass(frozen=True)
class ApproveArticleUseCase(LoggerMixin):
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

        if await self.feedback_repo.count_open(article_id) > 0:
            raise ArticleStateConflictError(
                "Cannot approve while feedback is still open"
            )

        drafts = await self.feedback_repo.list_by_article(
            article_id, statuses=[FeedbackStatus.DRAFT]
        )
        if drafts:
            self.log_warning(
                f"Approving article {article_id} with {len(drafts)} unpublished draft feedback(s) — they will be orphaned"
            )

        updated = await self.article_repo.update_status(
            article_id,
            status=ArticleStatus.APPROVED,
            reviewer_user_id=caller.id,
            set_reviewed_at=True,
            last_activity_by=caller.id,
            clear_reviewed_content=True,
        )
        if updated is None:
            raise ArticleNotFoundError()
        await self.event_repo.create(
            ArticleEvent(article_id=article_id, actor_id=caller.id, type=ArticleEventType.APPROVED)
        )
        self.log_info(f"Article approved: id={article_id} reviewer={caller.id}")
        return updated
