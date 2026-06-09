# app/modules/workspaces/data/model.py
from datetime import datetime
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
    NOT_SUBMITTED = "not_submitted"
    WAITING_FOR_REVIEW = "waiting_for_review"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"


class Workspace(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("ws"), alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    name_lower: str = Field(..., description="Lowercased name for unique index")
    owner_user_id: str = Field(..., description="Owning creator user id")

    class Config:
        collection_name = "workspaces"


class Article(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("art"), alias="_id")
    workspace_id: str = Field(..., description="Parent workspace id")
    name: str = Field(..., min_length=1, max_length=100)
    product: Product = Field(..., description="Closed-set product code, immutable")
    content: str = Field(default="", description="TipTap HTML; may be empty")
    status: ArticleStatus = Field(default=ArticleStatus.NOT_SUBMITTED)
    reviewer_user_id: Optional[str] = Field(default=None)
    reviewed_at: Optional[datetime] = Field(default=None)

    class Config:
        collection_name = "articles"
