# app/modules/workspaces/domain/usecases/start_review_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import Article, ArticleStatus
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    QcMisconfiguredError,
)
from app.modules.workspaces.domain.repo import ArticleRepo


@dataclass(frozen=True)
class StartReviewArticleUseCase(LoggerMixin):
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> Article:
        # 1. Load
        article = await self.article_repo.get_by_id(article_id)
        # 2. Workspace-id match
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()
        # 3. Product scope — skip for superuser; required for QC
        if caller.role != UserRole.SUPERUSER:
            if caller.qc_product is None:
                raise QcMisconfiguredError()
            if article.product != caller.qc_product:
                # Hide existence: same 404 as missing article.
                raise ArticleNotFoundError()
        # 4. Status
        if article.status != ArticleStatus.WAITING_FOR_REVIEW:
            raise ArticleStateConflictError(
                "Article is not waiting for review"
            )
        # 5. Apply
        updated = await self.article_repo.update_status(
            article_id,
            status=ArticleStatus.REVIEWING,
            reviewer_user_id=caller.id,
        )
        if updated is None:
            raise ArticleNotFoundError()
        self.log_info(f"Article moved to reviewing: id={article_id} reviewer={caller.id}")
        return updated
