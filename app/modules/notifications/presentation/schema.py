# app/modules/notifications/presentation/schema.py
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.modules.notifications.data.model import Notification, NotificationType


def _epoch_ms(dt) -> int:
    return int(dt.timestamp() * 1000)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=False)
    id: str
    article_id: str
    event_id: str
    type: NotificationType
    read_at: Optional[int] = None
    created_at: int

    @classmethod
    def from_model(cls, n: Notification) -> "NotificationResponse":
        return cls(
            id=n.id, article_id=n.article_id, event_id=n.event_id, type=n.type,
            read_at=_epoch_ms(n.read_at) if n.read_at else None,
            created_at=_epoch_ms(n.created_at),
        )


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
