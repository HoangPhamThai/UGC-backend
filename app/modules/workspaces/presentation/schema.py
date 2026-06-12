# app/modules/workspaces/presentation/schema.py
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.workspaces.data.model import (
    AnchorTargetType,
    Article,
    ArticleStatus,
    Feedback,
    FeedbackReply,
    FeedbackStatus,
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
    claimed_by: Optional[str] = None
    review_round: int = 0
    reject_reason: Optional[str] = None

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
            claimed_by=article.claimed_by,
            review_round=article.review_round,
            reject_reason=article.reject_reason,
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


# --- QC review requests ---

class AnchorRequest(BaseModel):
    target_type: AnchorTargetType
    quote: str = ""
    prefix: str = ""
    suffix: str = ""
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    image_ref: Optional[str] = None
    image_occurrence: Optional[int] = None


class CreateFeedbackRequest(BaseModel):
    body: str = Field(default="", max_length=5000)
    anchor: AnchorRequest


class SetFeedbackStatusRequest(BaseModel):
    status: Literal[FeedbackStatus.OPEN, FeedbackStatus.RESOLVED, FeedbackStatus.DISMISSED]


class AddReplyRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class RejectArticleRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=5000)


# --- QC review responses ---

class ReplyResponse(BaseModel):
    id: str
    author_id: str
    body: str
    created_at: int

    @classmethod
    def from_model(cls, r: FeedbackReply) -> "ReplyResponse":
        return cls(id=r.id, author_id=r.author_id, body=r.body,
                   created_at=_to_epoch_ms(r.created_at))


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str
    article_id: str
    author_id: str
    body: str
    status: FeedbackStatus
    anchor: AnchorRequest
    replies: list[ReplyResponse]
    resolved_by: Optional[str] = None
    resolved_at: Optional[int] = None
    created_at: int
    updated_at: int

    @classmethod
    def from_model(cls, f: Feedback) -> "FeedbackResponse":
        return cls(
            id=f.id, article_id=f.article_id, author_id=f.author_id, body=f.body,
            status=f.status,
            anchor=AnchorRequest(
                target_type=f.anchor.target_type, quote=f.anchor.quote,
                prefix=f.anchor.prefix, suffix=f.anchor.suffix,
                start_offset=f.anchor.start_offset, end_offset=f.anchor.end_offset,
                image_ref=f.anchor.image_ref, image_occurrence=f.anchor.image_occurrence,
            ),
            replies=[ReplyResponse.from_model(r) for r in f.replies],
            resolved_by=f.resolved_by,
            resolved_at=_to_epoch_ms(f.resolved_at) if f.resolved_at else None,
            created_at=_to_epoch_ms(f.created_at),
            updated_at=_to_epoch_ms(f.updated_at),
        )
