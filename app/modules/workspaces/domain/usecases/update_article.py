# app/modules/workspaces/domain/usecases/update_article.py
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.core.time import business_today
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import (
    EDITABLE_STATUSES,
    Article,
    Product,
)
from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    InvalidInputError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class UpdateArticleUseCase(LoggerMixin):
    """Edit any subset of an article's editable fields (name / product /
    on_air_date / content). Allowed only while the article is editable
    (article.md §4.3). Backs the unified PATCH endpoint and auto-save."""

    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self,
        *,
        workspace_id: str,
        article_id: str,
        caller: User,
        name: Optional[str] = None,
        product: Optional[Product] = None,
        on_air_date: Optional[date] = None,
        content: Optional[str] = None,
    ) -> Article:
        if name is None and product is None and on_air_date is None and content is None:
            raise InvalidInputError("No fields to update")

        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = await self.article_repo.get_by_id(article_id)
        if article is None or article.workspace_id != workspace_id:
            raise ArticleNotFoundError()

        if article.status not in EDITABLE_STATUSES:
            raise ArticleStateConflictError("Article is not in an editable state")

        # Validate the fields that are actually changing.
        trimmed_name: Optional[str] = None
        if name is not None:
            trimmed_name = name.strip()
            if not trimmed_name:
                raise InvalidInputError("name must not be empty")

        if on_air_date is not None and on_air_date < business_today():
            raise InvalidInputError("on_air_date must not be in the past")

        updated = await self.article_repo.update_fields(
            article_id,
            name=trimmed_name,
            product=product,
            on_air_date=on_air_date,
            content=content,
        )
        if updated is None:
            raise ArticleNotFoundError()
        return updated
