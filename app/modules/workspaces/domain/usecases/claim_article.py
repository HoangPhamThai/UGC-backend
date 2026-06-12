# app/modules/workspaces/domain/usecases/claim_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, ArticleEvent, ArticleEventType, AWAITING_QC_STATUSES
from app.modules.workspaces.domain.errors import ArticleNotFoundError, ArticleStateConflictError, ClaimConflictError
from app.modules.workspaces.domain.repo import ArticleEventRepo, ArticleRepo
from app.modules.workspaces.domain.usecases._review_guard import ensure_qc_scope


@dataclass(frozen=True)
class ClaimArticleUseCase(LoggerMixin):
    article_repo: ArticleRepo
    event_repo: ArticleEventRepo

    async def execute(self, *, workspace_id: str, article_id: str, caller: User) -> Article:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        ensure_qc_scope(article, caller)

        if article.status not in AWAITING_QC_STATUSES:
            raise ArticleStateConflictError("Article is not awaiting review")

        if article.claimed_by == caller.id:
            # Already held by this caller — claiming again is a no-op (no duplicate event).
            return article

        claimed = await self.article_repo.claim(article_id, caller.id)
        if claimed is None:
            # Either it vanished, or someone else holds it.
            raise ClaimConflictError()

        await self.event_repo.create(
            ArticleEvent(article_id=article_id, actor_id=caller.id, type=ArticleEventType.CLAIMED)
        )
        self.log_info(f"Article claimed: id={article_id} qc={caller.id}")
        return claimed
