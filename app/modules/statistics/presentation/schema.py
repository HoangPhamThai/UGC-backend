# app/modules/statistics/presentation/schema.py
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel

from app.core.model import to_epoch_ms
from app.modules.workspaces.data.model import ArticleStatus, PostMetrics, Product
from app.modules.statistics.domain.usecases.get_summary import SummaryCounts
from app.modules.statistics.domain.usecases.get_qc_breakdown import QcBreakdownRow
from app.modules.statistics.domain.usecases.list_creators import CreatorListEntry
from app.modules.statistics.domain.usecases.list_creator_articles import (
    CreatorArticleEntry,
)
from app.modules.statistics.domain.usecases.list_all_articles import ArticleRowEntry
from app.modules.statistics.domain.usecases.list_qc_articles import QcArticleEntry
from app.modules.statistics.domain.usecases.get_article_detail import (
    ArticleDetailEntry,
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
    claimed_by_email: Optional[str] = None
    reviewer_email: Optional[str] = None

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
            claimed_by_email=e.claimed_by_email,
            reviewer_email=e.reviewer_email,
        )


class CreatorArticlesResponse(BaseModel):
    items: list[CreatorArticleItemResponse]
    total: int


class MetricsBrief(BaseModel):
    """Curated engagement metrics for the analytics agent. Excludes heavy fields
    (images, comments_preview, content) and low-value ones. All optional — null
    means the article's link has not been scraped yet."""
    platform: Optional[str] = None
    views: Optional[int] = None
    favorites: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None

    @classmethod
    def from_metrics(cls, m: Optional[PostMetrics]) -> Optional["MetricsBrief"]:
        if m is None:
            return None
        return cls(
            platform=m.platform, views=m.views, favorites=m.favorites,
            comments=m.comments, shares=m.shares,
        )


class ArticleRowResponse(BaseModel):
    id: str
    name: str
    product: Product
    status: ArticleStatus
    on_air_date: date
    created_at: int  # epoch ms
    creator_email: Optional[str] = None
    claimed_by_email: Optional[str] = None
    reviewer_email: Optional[str] = None
    link: Optional[str] = None
    metrics: Optional[MetricsBrief] = None

    @classmethod
    def from_entry(cls, e: ArticleRowEntry) -> "ArticleRowResponse":
        return cls(
            id=e.id,
            name=e.name,
            product=e.product,
            status=e.status,
            on_air_date=e.on_air_date,
            created_at=to_epoch_ms(e.created_at),
            creator_email=e.creator_email,
            claimed_by_email=e.claimed_by_email,
            reviewer_email=e.reviewer_email,
            link=e.link,
            metrics=MetricsBrief.from_metrics(e.metrics),
        )


class ArticleListResponse(BaseModel):
    items: list[ArticleRowResponse]
    total: int


class QcArticleRowResponse(BaseModel):
    id: str
    name: str
    product: Product
    status: ArticleStatus
    on_air_date: date
    created_at: int  # epoch ms
    creator_email: Optional[str] = None
    outcome: Literal["approved", "auto_approved", "rejected", "in_review"]

    @classmethod
    def from_entry(cls, e: QcArticleEntry) -> "QcArticleRowResponse":
        return cls(
            id=e.id,
            name=e.name,
            product=e.product,
            status=e.status,
            on_air_date=e.on_air_date,
            created_at=to_epoch_ms(e.created_at),
            creator_email=e.creator_email,
            outcome=e.outcome,
        )


class QcArticlesResponse(BaseModel):
    items: list[QcArticleRowResponse]
    total: int


class ReviewSummaryResponse(BaseModel):
    review_round: int
    anchored_feedback_count: int
    general_feedback_count: int


class ArticleDetailResponse(BaseModel):
    id: str
    name: str
    product: Product
    status: ArticleStatus
    on_air_date: date
    created_at: int  # epoch ms
    link: Optional[str] = None
    link_submitted_at: Optional[int] = None  # epoch ms
    extraction_status: Optional[str] = None
    has_content: bool
    metrics: Optional[MetricsBrief] = None
    creator_email: Optional[str] = None
    claimed_by_email: Optional[str] = None
    reviewer_email: Optional[str] = None
    review: ReviewSummaryResponse

    @classmethod
    def from_entry(cls, e: ArticleDetailEntry) -> "ArticleDetailResponse":
        return cls(
            id=e.id,
            name=e.name,
            product=e.product,
            status=e.status,
            on_air_date=e.on_air_date,
            created_at=to_epoch_ms(e.created_at),
            link=e.link,
            link_submitted_at=to_epoch_ms(e.link_submitted_at) if e.link_submitted_at else None,
            extraction_status=e.extraction_status,
            has_content=e.has_content,
            metrics=MetricsBrief.from_metrics(e.metrics),
            creator_email=e.creator_email,
            claimed_by_email=e.claimed_by_email,
            reviewer_email=e.reviewer_email,
            review=ReviewSummaryResponse(
                review_round=e.review_round,
                anchored_feedback_count=e.anchored_feedback_count,
                general_feedback_count=e.general_feedback_count,
            ),
        )
