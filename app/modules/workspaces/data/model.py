# app/modules/workspaces/data/model.py
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

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


class FeedbackStatus(str, Enum):
    """Feedback lifecycle. See qc-review.md §6."""
    DRAFT = "draft"          # being composed in a review session; creator can't see it
    OPEN = "open"            # published; blocking
    RESOLVED = "resolved"    # QC accepted the fix
    DISMISSED = "dismissed"  # QC withdrew the feedback


class AnchorTargetType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    NONE = "none"


class ArticleEventType(str, Enum):
    """Append-only audit log event types. See qc-review.md §4.5."""
    SUBMITTED = "submitted"
    WITHDRAWN = "withdrawn"
    CLAIMED = "claimed"
    REVIEW_PUBLISHED = "review_published"
    FEEDBACK_RESOLVED = "feedback_resolved"
    FEEDBACK_DISMISSED = "feedback_dismissed"
    FEEDBACK_REOPENED = "feedback_reopened"
    REPLY_ADDED = "reply_added"
    EDITED_RESUBMITTED = "edited_resubmitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"



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
    reviewed_content: Optional[str] = Field(
        default=None,
        description="HTML snapshot at last QC publish; cleared on terminal status",
    )
    on_air_date: date = Field(
        ...,
        description="Go-live calendar date; not in the past at create/update. "
        "Stored as midnight-UTC datetime (bson cannot encode a bare date).",
    )
    status: ArticleStatus = Field(default=ArticleStatus.NOT_SUBMITTED)
    reviewer_user_id: Optional[str] = Field(default=None)
    reviewed_at: Optional[datetime] = Field(default=None)

    # --- QC review (qc-review.md §4.1) ---
    claimed_by: Optional[str] = Field(
        default=None, description="QC currently holding the article (sticky claim lock)"
    )
    claimed_at: Optional[datetime] = Field(default=None)
    reject_reason: Optional[str] = Field(
        default=None, description="Required reason captured at reject time"
    )
    rejected_by: Optional[str] = Field(default=None)
    rejected_at: Optional[datetime] = Field(default=None)
    review_round: int = Field(
        default=0, description="Incremented each time the article flips to feedback_provided"
    )
    last_activity_by: Optional[str] = Field(default=None)
    last_activity_at: Optional[datetime] = Field(default=None)

    class Config:
        collection_name = "articles"


class FeedbackAnchor(BaseModel):
    """Content-based anchor (qc-review.md §4.3, §7). Embedded 1:1 in Feedback."""
    target_type: AnchorTargetType
    quote: str = Field(default="")
    prefix: str = Field(default="")
    suffix: str = Field(default="")
    start_offset: Optional[int] = Field(default=None, description="code-point offset hint")
    end_offset: Optional[int] = Field(default=None)
    image_ref: Optional[str] = Field(default=None, description="content hash of the <img>")
    image_occurrence: Optional[int] = Field(
        default=None, description="tie-breaker when the same image appears multiple times"
    )


class FeedbackReply(BaseModel):
    """Flat reply inside a feedback thread (qc-review.md §4.4)."""
    id: str = Field(default_factory=lambda: make_prefixed_id("rep"))
    author_id: str
    body: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Feedback(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("fb"), alias="_id")
    article_id: str
    author_id: str = Field(..., description="QC who created the feedback")
    body: str = Field(default="")
    status: FeedbackStatus = Field(default=FeedbackStatus.DRAFT)
    anchor: FeedbackAnchor
    replies: list[FeedbackReply] = Field(default_factory=list)
    resolved_by: Optional[str] = Field(default=None)
    resolved_at: Optional[datetime] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def _default_null_anchor(cls, data: Any) -> Any:
        # Legacy rows (pre-anchor MVP) may have anchor=null — coerce so list/get works.
        if isinstance(data, dict) and not data.get("anchor"):
            return {
                **data,
                "anchor": {"target_type": AnchorTargetType.NONE},
            }
        return data

    class Config:
        collection_name = "feedbacks"


class ArticleEvent(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("evt"), alias="_id")
    article_id: str
    actor_id: str = Field(..., description="User id, or a system actor for the cron job")
    type: ArticleEventType
    payload: dict = Field(default_factory=dict)

    class Config:
        collection_name = "article_events"
