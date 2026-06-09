# app/modules/workspaces/presentation/schema.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

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


class UpdateArticleContentRequest(BaseModel):
    content: str = Field(default="")


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
