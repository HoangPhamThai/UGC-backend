# app/modules/workspaces/domain/usecases/get_workspace.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.core.permissions import Permission, has_permission
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, Product, Workspace
from app.modules.workspaces.domain.errors import (
    QcMisconfiguredError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class GetWorkspaceResult:
    workspace: Workspace
    articles: list[Article]
    products: list[Product]


@dataclass(frozen=True)
class GetWorkspaceUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(self, *, workspace_id: str, caller: User) -> GetWorkspaceResult:
        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None:
            raise WorkspaceNotFoundError()

        # Owner sees everything in their workspace.
        if caller.id == ws.owner_user_id:
            articles = await self.article_repo.list_by_workspace(workspace_id)
            products = self._distinct_products(articles)
            return GetWorkspaceResult(ws, articles, products)

        # Admin / superuser: see everything.
        if has_permission(caller, Permission.WORKSPACES_READ_ANY):
            articles = await self.article_repo.list_by_workspace(workspace_id)
            products = self._distinct_products(articles)
            return GetWorkspaceResult(ws, articles, products)

        # QC: scoped to their assigned products.
        if has_permission(caller, Permission.WORKSPACES_READ_BY_PRODUCT):
            if not caller.qc_products:
                raise QcMisconfiguredError()
            if not await self.article_repo.workspace_has_any_product(
                workspace_id, caller.qc_products
            ):
                # Workspace exists but is invisible to this QC.
                raise WorkspaceNotFoundError()
            articles = await self.article_repo.list_by_workspace(
                workspace_id, products=caller.qc_products
            )
            return GetWorkspaceResult(ws, articles, self._distinct_products(articles))

        # Anyone else (e.g. another creator).
        raise WorkspaceNotFoundError()

    @staticmethod
    def _distinct_products(articles: list[Article]) -> list[Product]:
        unique = {a.product for a in articles}
        return sorted(unique, key=lambda p: list(Product).index(p))
