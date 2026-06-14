# app/modules/reports/presentation/schema.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.model import to_epoch_ms as _to_epoch_ms
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.repo import EligibleArticle
from app.modules.reports.domain.usecases.list_eligible import EligibleCreatorGroup


# --- Requests ---
class GenerateReportsRequest(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    article_award_price: int = Field(..., ge=0)
    tax_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="e.g. 0.10 for 10%")
    creator_user_id: Optional[str] = Field(default=None)


# --- Responses ---
class EligibleArticleResponse(BaseModel):
    article_id: str
    name: str
    product: str
    platform: Optional[str] = None
    on_air_date: str
    link: str
    views: Optional[int] = None

    @classmethod
    def from_entity(cls, a: EligibleArticle) -> "EligibleArticleResponse":
        return cls(
            article_id=a.article_id, name=a.name, product=a.product,
            platform=a.platform, on_air_date=a.on_air_date.isoformat(),
            link=a.link, views=a.views,
        )


class EligibleGroupResponse(BaseModel):
    creator_user_id: str
    email: str
    profile_complete: bool
    article_count: int
    articles: list[EligibleArticleResponse]

    @classmethod
    def from_group(cls, g: EligibleCreatorGroup) -> "EligibleGroupResponse":
        return cls(
            creator_user_id=g.creator_user_id, email=g.email,
            profile_complete=g.profile_complete, article_count=g.article_count,
            articles=[EligibleArticleResponse.from_entity(a) for a in g.articles],
        )


class ReportResponse(BaseModel):
    id: str
    period: str
    creator_user_id: str
    status: ReportStatus
    total_approved_articles: int
    article_award_price: int
    total_award: int
    tax: int
    final_award: int
    final_award_verbal: str
    created_at: int
    finalized_at: Optional[int] = None

    @classmethod
    def from_model(cls, r: AcceptanceReport) -> "ReportResponse":
        return cls(
            id=r.id, period=r.period, creator_user_id=r.creator_user_id,
            status=r.status, total_approved_articles=r.total_approved_articles,
            article_award_price=r.article_award_price, total_award=r.total_award,
            tax=r.tax, final_award=r.final_award, final_award_verbal=r.final_award_verbal,
            created_at=_to_epoch_ms(r.created_at),
            finalized_at=_to_epoch_ms(r.finalized_at) if r.finalized_at else None,
        )
