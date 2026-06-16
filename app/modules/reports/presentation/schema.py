# app/modules/reports/presentation/schema.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.model import to_epoch_ms as _to_epoch_ms
from app.modules.reports.data.model import AcceptanceReport, LineItem, ReportStatus
from app.modules.reports.domain.repo import EligibleArticle
from app.modules.reports.domain.usecases.list_eligible import EligibleCreatorGroup
from app.modules.reports.domain.usecases.recheck_link_metrics import RecheckResult
from app.modules.reports.domain.usecases.report_statistics import ReportStatistics
from app.modules.reports.domain.usecases.template import TemplateView
from app.modules.workspaces.data.model import PostMetrics


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
    creator_email: Optional[str] = None
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
    def from_model(cls, r: AcceptanceReport, email: Optional[str] = None) -> "ReportResponse":
        return cls(
            id=r.id, period=r.period, creator_user_id=r.creator_user_id,
            creator_email=email,
            status=r.status, total_approved_articles=r.total_approved_articles,
            article_award_price=r.article_award_price, total_award=r.total_award,
            tax=r.tax, final_award=r.final_award, final_award_verbal=r.final_award_verbal,
            created_at=_to_epoch_ms(r.created_at),
            finalized_at=_to_epoch_ms(r.finalized_at) if r.finalized_at else None,
        )


class ReportStatisticsResponse(BaseModel):
    period: Optional[str] = None
    draft_count: int
    final_count: int
    creator_count: int
    total_final_award: int

    @classmethod
    def from_stats(cls, s: ReportStatistics) -> "ReportStatisticsResponse":
        return cls(
            period=s.period, draft_count=s.draft_count, final_count=s.final_count,
            creator_count=s.creator_count, total_final_award=s.total_final_award,
        )


class RecheckResponse(BaseModel):
    stored: Optional[PostMetrics] = None
    fresh: PostMetrics
    diff: dict

    @classmethod
    def from_result(cls, r: RecheckResult) -> "RecheckResponse":
        return cls(stored=r.stored, fresh=r.fresh, diff=r.diff)


class TemplateMetaResponse(BaseModel):
    filename: str
    uploaded_by: Optional[str] = None
    uploaded_at: Optional[int] = None
    is_default: bool

    @classmethod
    def from_view(cls, v: TemplateView) -> "TemplateMetaResponse":
        return cls(
            filename=v.filename,
            uploaded_by=v.uploaded_by,
            uploaded_at=_to_epoch_ms(v.uploaded_at) if v.uploaded_at else None,
            is_default=v.is_default,
        )


def _content_type_from_key(key: str) -> str:
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    return {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "gif": "image/gif", "webp": "image/webp",
    }.get(ext, "application/octet-stream")


class SaveRulesRequest(BaseModel):
    source_markdown: str = ""
    ir: dict


class RulesResponse(BaseModel):
    source_markdown: str
    ir: dict
    warnings: list[dict]
    status: str


class FieldRegistryEntry(BaseModel):
    key: str
    scope: str
    type: str
    writable: bool
    description: str
    enum_values: Optional[list[str]] = None


class LineItemResponse(BaseModel):
    article_id: str
    seq: int
    platform: Optional[str]
    on_air_date: str
    link: Optional[str]
    views: Optional[int]
    has_image: bool

    @classmethod
    def from_line_item(cls, li: LineItem) -> "LineItemResponse":
        return cls(
            article_id=li.article_id, seq=li.seq, platform=li.platform,
            on_air_date=li.on_air_date, link=li.link, views=li.views,
            has_image=li.article_image is not None,
        )


class ReportDetailResponse(ReportResponse):
    line_items: list[LineItemResponse]

    @classmethod
    def from_detail_model(cls, r: AcceptanceReport, email: Optional[str] = None) -> "ReportDetailResponse":
        base = ReportResponse.from_model(r, email)
        return cls(
            **base.model_dump(),
            line_items=[LineItemResponse.from_line_item(li) for li in r.line_items],
        )
