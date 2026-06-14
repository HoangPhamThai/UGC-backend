# app/modules/workspaces/domain/usecases/get_article.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.core.permissions import Permission, has_permission
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    QcMisconfiguredError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class GetArticleUseCase(LoggerMixin):
    """Fetch a single article, scoped to the caller's workspace visibility
    (mirrors GetWorkspaceUseCase: owner / WORKSPACES_READ_ANY / QC-by-product)."""

    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self, *, workspace_id: str, article_id: str, caller: User
    ) -> Article:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        if caller.id == ws.owner_user_id:
            return article
        if has_permission(caller, Permission.WORKSPACES_READ_ANY):
            return article
        if has_permission(caller, Permission.WORKSPACES_READ_BY_PRODUCT):
            if not caller.qc_products:
                raise QcMisconfiguredError()
            if article.product in caller.qc_products:
                return article
            raise WorkspaceNotFoundError()
        raise WorkspaceNotFoundError()
