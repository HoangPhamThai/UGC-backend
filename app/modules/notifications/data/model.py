# app/modules/notifications/data/model.py
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class NotificationType(str, Enum):
    """In-app notification kinds. See qc-review.md §8.2."""
    FEEDBACK_PROVIDED = "feedback_provided"   # QC published a review round -> creator
    REPLY = "reply"                            # someone replied in a thread -> other party
    APPROVED = "approved"                      # -> creator
    REJECTED = "rejected"                      # -> creator
    EDITED_RESUBMITTED = "edited_resubmitted"  # creator resubmitted -> claiming QC


class Notification(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("ntf"), alias="_id")
    recipient_id: str
    article_id: str
    event_id: str = Field(..., description="Source ARTICLE_EVENT id")
    type: NotificationType
    read_at: Optional[datetime] = Field(default=None)
    workspace_id: Optional[str] = None

    class Config:
        collection_name = "notifications"
