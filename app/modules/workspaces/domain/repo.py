# app/modules/workspaces/domain/repo.py
from abc import ABC, abstractmethod
from typing import Optional

from app.modules.workspaces.data.model import Article, ArticleStatus, Product, Workspace


class WorkspaceRepo(ABC):

    @abstractmethod
    async def create(self, workspace: Workspace) -> Workspace: ...

    @abstractmethod
    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]: ...

    @abstractmethod
    async def list_by_owner(
        self, owner_user_id: str, *, skip: int, limit: int
    ) -> list[Workspace]: ...

    @abstractmethod
    async def count_by_owner(self, owner_user_id: str) -> int: ...

    @abstractmethod
    async def list_all(self, *, skip: int, limit: int) -> list[Workspace]: ...

    @abstractmethod
    async def count_all(self) -> int: ...

    @abstractmethod
    async def list_with_product(
        self, product: Product, *, skip: int, limit: int
    ) -> list[Workspace]: ...

    @abstractmethod
    async def count_with_product(self, product: Product) -> int: ...

    @abstractmethod
    async def delete(self, workspace_id: str) -> None: ...

    @abstractmethod
    async def article_counts(
        self, workspace_ids: list[str], *, product: Optional[Product] = None
    ) -> dict[str, int]: ...

    @abstractmethod
    async def products_for(self, workspace_ids: list[str]) -> dict[str, list[Product]]: ...


class ArticleRepo(ABC):

    @abstractmethod
    async def create(self, article: Article) -> Article: ...

    @abstractmethod
    async def get_by_id(self, article_id: str) -> Optional[Article]: ...

    @abstractmethod
    async def list_by_workspace(
        self, workspace_id: str, *, product: Optional[Product] = None
    ) -> list[Article]: ...

    @abstractmethod
    async def workspace_has_product(self, workspace_id: str, product: Product) -> bool: ...

    @abstractmethod
    async def update_content(self, article_id: str, content: str) -> Optional[Article]: ...

    @abstractmethod
    async def update_status(
        self,
        article_id: str,
        *,
        status: ArticleStatus,
        reviewer_user_id: Optional[str] = None,
        set_reviewed_at: bool = False,
    ) -> Optional[Article]: ...

    @abstractmethod
    async def delete(self, article_id: str) -> None: ...

    @abstractmethod
    async def delete_by_workspace(self, workspace_id: str) -> int: ...
