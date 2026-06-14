# app/modules/statistics/presentation/schema.py
from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.core.model import to_epoch_ms
from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.usecases.get_summary import SummaryCounts
from app.modules.statistics.domain.usecases.get_qc_breakdown import QcBreakdownRow
from app.modules.statistics.domain.usecases.list_creators import CreatorListEntry
from app.modules.statistics.domain.usecases.list_creator_articles import (
    CreatorArticleEntry,
)


class SummaryResponse(BaseModel):
    total: int
    awaiting_review: int
    in_review: int
    approved: int
    rejected: int
    auto_approved: int

    @classmethod
    def from_counts(cls, c: SummaryCounts) -> "SummaryResponse":
        return cls(
            total=c.total,
            awaiting_review=c.awaiting_review,
            in_review=c.in_review,
            approved=c.approved,
            rejected=c.rejected,
            auto_approved=c.auto_approved,
        )


class QcBreakdownRowResponse(BaseModel):
    qc_id: str
    email: str
    products: list[Product]
    claimed: int
    approved: int
    rejected: int
    auto_approved_after_claim: int

    @classmethod
    def from_row(cls, r: QcBreakdownRow) -> "QcBreakdownRowResponse":
        return cls(
            qc_id=r.qc_id,
            email=r.email,
            products=r.products,
            claimed=r.claimed,
            approved=r.approved,
            rejected=r.rejected,
            auto_approved_after_claim=r.auto_approved_after_claim,
        )


class QcBreakdownResponse(BaseModel):
    items: list[QcBreakdownRowResponse]


class CreatorListItemResponse(BaseModel):
    id: str
    email: str
    article_count_in_window: int

    @classmethod
    def from_entry(cls, e: CreatorListEntry) -> "CreatorListItemResponse":
        return cls(
            id=e.id, email=e.email, article_count_in_window=e.article_count_in_window
        )


class CreatorListResponse(BaseModel):
    items: list[CreatorListItemResponse]
    total: int


class CreatorArticleItemResponse(BaseModel):
    id: str
    name: str
    product: Product
    status: ArticleStatus
    on_air_date: date
    created_at: int  # epoch ms
    claimed_by: Optional[str] = None
    reviewer_user_id: Optional[str] = None

    @classmethod
    def from_entry(cls, e: CreatorArticleEntry) -> "CreatorArticleItemResponse":
        return cls(
            id=e.id,
            name=e.name,
            product=e.product,
            status=e.status,
            on_air_date=e.on_air_date,
            created_at=to_epoch_ms(e.created_at),
            claimed_by=e.claimed_by,
            reviewer_user_id=e.reviewer_user_id,
        )


class CreatorArticlesResponse(BaseModel):
    items: list[CreatorArticleItemResponse]
    total: int
