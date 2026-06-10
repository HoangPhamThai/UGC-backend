# app/modules/workspaces/domain/usecases/list_workspaces.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.core.permissions import Permission, has_permission
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Product, Workspace
from app.modules.workspaces.domain.errors import QcMisconfiguredError
from app.modules.workspaces.domain.repo import WorkspaceRepo


@dataclass(frozen=True)
class ListWorkspacesResult:
    items: list[Workspace]
    total: int
    article_counts: dict[str, int]
    products_by_ws: dict[str, list[Product]]


@dataclass(frozen=True)
class ListWorkspacesUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo

    async def execute(
        self, *, caller: User, page: int, limit: int
    ) -> ListWorkspacesResult:
        skip = (page - 1) * limit
        repo = self.workspace_repo

        if has_permission(caller, Permission.WORKSPACES_READ_ANY):
            workspaces = await repo.list_all(skip=skip, limit=limit)
            total = await repo.count_all()
            ids = [w.id for w in workspaces]
            counts = {w.id: w.article_count for w in workspaces}
            products = await repo.products_for(ids)
            return ListWorkspacesResult(workspaces, total, counts, products)

        if has_permission(caller, Permission.WORKSPACES_READ_BY_PRODUCT):
            if caller.qc_product is None:
                raise QcMisconfiguredError()
            p = caller.qc_product
            workspaces = await repo.list_with_product(p, skip=skip, limit=limit)
            total = await repo.count_with_product(p)
            ids = [w.id for w in workspaces]
            # QC sees only their product, so the count must be filtered;
            # the denormalized total on the workspace doc isn't usable here.
            counts = await repo.article_counts(ids, product=p)
            products = {wid: [p] for wid in ids}
            return ListWorkspacesResult(workspaces, total, counts, products)

        # Creator (default): own workspaces only.
        workspaces = await repo.list_by_owner(caller.id, skip=skip, limit=limit)
        total = await repo.count_by_owner(caller.id)
        counts = {w.id: w.article_count for w in workspaces}
        products = await repo.products_for([w.id for w in workspaces])
        return ListWorkspacesResult(workspaces, total, counts, products)
