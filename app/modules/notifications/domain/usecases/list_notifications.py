# app/modules/notifications/domain/usecases/list_notifications.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.notifications.data.model import Notification
from app.modules.notifications.domain.repo import NotificationRepo


@dataclass(frozen=True)
class NotificationListResult:
    items: list[Notification]
    total: int
    unread_count: int


@dataclass(frozen=True)
class ListNotificationsUseCase(LoggerMixin):
    notification_repo: NotificationRepo

    async def execute(
        self, *, recipient_id: str, unread_only: bool, page: int, limit: int
    ) -> NotificationListResult:
        skip = (page - 1) * limit
        items = await self.notification_repo.list_for_recipient(
            recipient_id, unread_only=unread_only, skip=skip, limit=limit
        )
        total = await self.notification_repo.count_for_recipient(
            recipient_id, unread_only=unread_only
        )
        unread = await self.notification_repo.count_unread(recipient_id)
        return NotificationListResult(items=items, total=total, unread_count=unread)
