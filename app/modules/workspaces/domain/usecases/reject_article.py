# app/modules/workspaces/domain/usecases/reject_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import (
    AWAITING_QC_STATUSES,
    Article,
    ArticleEvent,
    ArticleEventType,
)
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    InvalidInputError,
)
from app.modules.workspaces.domain.repo import ArticleEventRepo, ArticleRepo
from app.modules.workspaces.domain.usecases._review_guard import (
    ensure_claimed_by_caller,
    ensure_qc_scope,
)


@dataclass(frozen=True)
class RejectArticleUseCase(LoggerMixin):
    article_repo: ArticleRepo
    event_repo: ArticleEventRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User, reason: str
    ) -> Article:
        cleaned = (reason or "").strip()
        if not cleaned:
            raise InvalidInputError("A rejection reason is required")

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        ensure_qc_scope(article, caller)
        if article.status not in AWAITING_QC_STATUSES:
            raise ArticleStateConflictError("Article is not awaiting review")
        ensure_claimed_by_caller(article, caller)

        updated = await self.article_repo.reject(
            article_id, reviewer_user_id=caller.id, reason=cleaned
        )
        if updated is None:
            raise ArticleNotFoundError()
        await self.event_repo.create(
            ArticleEvent(article_id=article_id, actor_id=caller.id, type=ArticleEventType.REJECTED)
        )
        self.log_info(f"Article rejected: id={article_id} reviewer={caller.id}")
        return updated
