# app/modules/notifications/domain/repo.py
from abc import ABC, abstractmethod
from typing import Optional

from app.modules.notifications.data.model import Notification


class NotificationRepo(ABC):

    @abstractmethod
    async def create(self, notification: Notification) -> Notification: ...

    @abstractmethod
    async def list_for_recipient(
        self, recipient_id: str, *, unread_only: bool, skip: int, limit: int
    ) -> list[Notification]: ...

    @abstractmethod
    async def count_for_recipient(
        self, recipient_id: str, *, unread_only: bool
    ) -> int: ...

    async def count_unread(self, recipient_id: str) -> int:
        """Convenience: unread count = count_for_recipient(unread_only=True)."""
        return await self.count_for_recipient(recipient_id, unread_only=True)

    @abstractmethod
    async def mark_read(
        self, notification_id: str, recipient_id: str
    ) -> Optional[Notification]:
        """Set read_at if not already read. Scoped to recipient (can't read others'
        notifications). Returns updated doc, or None if not found / not owned."""
        ...

    @abstractmethod
    async def mark_all_read(self, recipient_id: str) -> int:
        """Mark all of the recipient's unread notifications read. Returns count."""
        ...
