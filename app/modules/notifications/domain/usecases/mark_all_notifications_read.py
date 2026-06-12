# app/modules/notifications/domain/usecases/mark_all_notifications_read.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.notifications.domain.repo import NotificationRepo


@dataclass(frozen=True)
class MarkAllNotificationsReadUseCase(LoggerMixin):
    notification_repo: NotificationRepo

    async def execute(self, *, recipient_id: str) -> int:
        return await self.notification_repo.mark_all_read(recipient_id)
