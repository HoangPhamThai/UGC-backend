# app/modules/workspaces/domain/usecases/create_article.py
from dataclasses import dataclass
from datetime import date

from app.core.logging_mixin import LoggerMixin
from app.core.time import business_today
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, ArticleStatus, Product
from app.modules.workspaces.domain.errors import (
    InvalidInputError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


@dataclass(frozen=True)
class CreateArticleUseCase(LoggerMixin):
    workspace_repo: WorkspaceRepo
    article_repo: ArticleRepo

    async def execute(
        self,
        *,
        workspace_id: str,
        name: str,
        product: Product,
        on_air_date: date,
        caller: User,
    ) -> Article:
        trimmed = name.strip()
        if not trimmed:
            raise InvalidInputError("name must not be empty")

        if on_air_date < business_today():
            raise InvalidInputError("on_air_date must not be in the past")

        ws = await self.workspace_repo.get_by_id(workspace_id)
        if ws is None or ws.owner_user_id != caller.id:
            raise WorkspaceNotFoundError()

        article = Article(
            workspace_id=workspace_id,
            name=trimmed,
            product=product,
            content="",
            on_air_date=on_air_date,
            status=ArticleStatus.NOT_SUBMITTED,
        )
        created = await self.article_repo.create(article)
        await self.workspace_repo.increment_article_count(workspace_id, by=1)
        self.log_info(
            f"Article created: id={created.id} ws={workspace_id} product={product.value}"
        )
        return created
