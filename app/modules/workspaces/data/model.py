# app/modules/workspaces/data/model.py
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class Product(str, Enum):
    """Closed set of products. See UGC/__documents__/workspace.md §2.3.

    Adding a value requires updating the business doc first.
    """
    CL = "CL"
    MMF = "MMF"
    FD = "FD"
    PL = "PL"
    FC = "FC"
    IN = "IN"
    STOCK = "Stock"
    TRANSFER = "Transfer"
    TELCO = "Telco"
    GLOBAL = "Global"
    OTA = "OTA"
    MOVIE = "Movie"


class ArticleStatus(str, Enum):
    """Article approval lifecycle. See article.md §4."""
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    FEEDBACK_PROVIDED = "feedback_provided"
    EDITED = "edited"
    APPROVED = "approved"
    REJECTED = "rejected"


# Shared status groupings (single source of truth for the use cases).
# Creator may edit content + attributes only in these states (article.md §4.3).
EDITABLE_STATUSES: frozenset[ArticleStatus] = frozenset(
    {ArticleStatus.NOT_SUBMITTED, ArticleStatus.FEEDBACK_PROVIDED}
)
# Final states — locked; auto-approve cron skips these (article.md §4.2/§4.4).
TERMINAL_STATUSES: frozenset[ArticleStatus] = frozenset(
    {ArticleStatus.APPROVED, ArticleStatus.REJECTED}
)
# Awaiting a QC decision — the only states QC may act on (article.md §4.2).
AWAITING_QC_STATUSES: frozenset[ArticleStatus] = frozenset(
    {ArticleStatus.SUBMITTED, ArticleStatus.EDITED}
)


class Workspace(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("ws"), alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    owner_user_id: str = Field(..., description="Owning creator user id")
    article_count: int = Field(
        default=0,
        description="Denormalized count of articles in this workspace; maintained by create/delete-article use cases. Not strictly validated — drift is possible if mutations crash between collections; reconcile by aggregating the articles collection.",
    )

    class Config:
        collection_name = "workspaces"


class Article(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("art"), alias="_id")
    workspace_id: str = Field(..., description="Parent workspace id")
    name: str = Field(..., min_length=1, max_length=100)
    product: Product = Field(
        ..., description="Closed-set product code; editable while status is editable"
    )
    content: str = Field(default="", description="TipTap HTML; may be empty")
    on_air_date: date = Field(
        ...,
        description="Go-live calendar date; not in the past at create/update. "
        "Stored as midnight-UTC datetime (bson cannot encode a bare date).",
    )
    status: ArticleStatus = Field(default=ArticleStatus.NOT_SUBMITTED)
    reviewer_user_id: Optional[str] = Field(default=None)
    reviewed_at: Optional[datetime] = Field(default=None)

    class Config:
        collection_name = "articles"
