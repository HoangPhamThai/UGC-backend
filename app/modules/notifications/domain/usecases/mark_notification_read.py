# app/modules/notifications/domain/usecases/mark_notification_read.py
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.notifications.data.model import Notification
from app.modules.notifications.domain.repo import NotificationRepo


@dataclass(frozen=True)
class MarkNotificationReadUseCase(LoggerMixin):
    notification_repo: NotificationRepo

    async def execute(self, *, notification_id: str, recipient_id: str) -> Optional[Notification]:
        return await self.notification_repo.mark_read(notification_id, recipient_id)
