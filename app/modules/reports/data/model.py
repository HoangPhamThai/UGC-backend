# app/modules/reports/data/model.py
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.core.model import BaseMongoModel, make_prefixed_id


class ReportStatus(str, Enum):
    """Acceptance report lifecycle (spec §7). Drafts are admin-only; finals are
    visible to the matching creator too. Amended = a final that was cancelled."""
    DRAFT = "draft"
    REVIEWING = "reviewing"
    FINAL = "final"
    AMENDED = "amended"


class LineItem(BaseModel):
    """One row of the Điều 2 table — a snapshotted approved+extracted article."""
    article_id: str
    seq: int = Field(..., description="1..N row number ({article_id_autoinc})")
    platform: Optional[str] = None
    on_air_date: str = Field(..., description="ISO date string for {article_on_air}")
    link: Optional[str] = None
    views: Optional[int] = None
    article_image: Optional[str] = Field(default=None, description="MinIO object key for article image")
    article_bonus_money: str = Field(default="  ", description="Bonus money placeholder — whitespace")


class AcceptanceReport(BaseMongoModel):
    """Immutable per-creator monthly acceptance report (spec §3.4). Snapshots the
    creator profile + line items at draft time; unique on (creator_user_id,
    period) among non-deleted reports."""
    id: str = Field(default_factory=lambda: make_prefixed_id("rpt"), alias="_id")
    period: str = Field(..., description="'YYYY-MM'; matched against on_air_date")
    creator_user_id: str
    status: ReportStatus = Field(default=ReportStatus.DRAFT)
    created_by: str = Field(..., description="admin user id")
    finalized_by: Optional[str] = Field(default=None)
    finalized_at: Optional[datetime] = Field(default=None)
    cancelled_by: Optional[str] = Field(default=None)
    cancelled_at: Optional[datetime] = Field(default=None)

    creator_snapshot: dict = Field(
        default_factory=dict, description="CreatorProfile fields frozen at draft time"
    )
    line_items: list[LineItem] = Field(default_factory=list)

    # Financials (admin-entered + computed at draft time)
    article_award_price: int = 0
    total_approved_articles: int = 0
    total_award: int = 0
    tax: int = Field(default=0, description="computed = round(total_award * tax_rate)")
    final_award: int = 0
    final_award_verbal: str = ""

    object_key: str = Field(..., description="MinIO key of the rendered .docx")

    class Config:
        collection_name = "acceptance_reports"
