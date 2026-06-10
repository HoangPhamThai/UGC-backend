# app/modules/workspaces/presentation/schema.py
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.workspaces.data.model import (
    Article,
    ArticleStatus,
    Product,
    Workspace,
)


# --- Requests ---


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class CreateArticleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    product: Product
    on_air_date: date


class UpdateArticleRequest(BaseModel):
    """Unified article update — any subset of editable fields; at least one
    required. `content` defaults to unset (None) so it is only written when the
    caller actually sends it."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    product: Optional[Product] = None
    on_air_date: Optional[date] = None
    content: Optional[str] = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "UpdateArticleRequest":
        if (
            self.name is None
            and self.product is None
            and self.on_air_date is None
            and self.content is None
        ):
            raise ValueError("at least one field must be provided")
        return self


# --- Responses ---


def _to_epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class ArticleResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str
    workspace_id: str
    name: str
    product: Product
    content: str
    status: ArticleStatus
    on_air_date: date
    created_at: int
    updated_at: int

    @classmethod
    def from_model(cls, article: Article) -> "ArticleResponse":
        return cls(
            id=article.id,
            workspace_id=article.workspace_id,
            name=article.name,
            product=article.product,
            content=article.content,
            status=article.status,
            on_air_date=article.on_air_date,
            created_at=_to_epoch_ms(article.created_at),
            updated_at=_to_epoch_ms(article.updated_at),
        )


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    owner_user_id: str
    created_at: int
    updated_at: int
    article_count: Optional[int] = None
    products: Optional[list[Product]] = None
    articles: Optional[list[ArticleResponse]] = None

    @classmethod
    def from_model(
        cls,
        ws: Workspace,
        *,
        articles: Optional[list[Article]] = None,
        article_count: Optional[int] = None,
        products: Optional[list[Product]] = None,
    ) -> "WorkspaceResponse":
        return cls(
            id=ws.id,
            name=ws.name,
            owner_user_id=ws.owner_user_id,
            created_at=_to_epoch_ms(ws.created_at),
            updated_at=_to_epoch_ms(ws.updated_at),
            article_count=article_count,
            products=products,
            articles=[ArticleResponse.from_model(a) for a in articles]
            if articles is not None
            else None,
        )


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceResponse]
    total: int
