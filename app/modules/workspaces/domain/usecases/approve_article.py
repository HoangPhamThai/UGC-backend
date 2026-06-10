# app/modules/workspaces/domain/usecases/approve_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import (
    AWAITING_QC_STATUSES,
    Article,
    ArticleStatus,
)
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    QcMisconfiguredError,
)
from app.modules.workspaces.domain.repo import ArticleRepo


@dataclass(frozen=True)
class ApproveArticleUseCase(LoggerMixin):
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> Article:
        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        if caller.role != UserRole.SUPERUSER:
            if caller.qc_product is None:
                raise QcMisconfiguredError()
            if article.product != caller.qc_product:
                raise ArticleNotFoundError()
        if article.status not in AWAITING_QC_STATUSES:
            raise ArticleStateConflictError("Article is not awaiting review")
        updated = await self.article_repo.update_status(
            article_id,
            status=ArticleStatus.APPROVED,
            set_reviewed_at=True,
        )
        if updated is None:
            raise ArticleNotFoundError()
        self.log_info(f"Article approved: id={article_id} reviewer={caller.id}")
        return updated
