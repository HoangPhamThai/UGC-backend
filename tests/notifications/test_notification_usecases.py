import pytest

from app.modules.notifications.data.model import Notification, NotificationType
from app.modules.notifications.domain.usecases.list_notifications import ListNotificationsUseCase
from app.modules.notifications.domain.usecases.mark_notification_read import MarkNotificationReadUseCase
from app.modules.notifications.domain.usecases.mark_all_notifications_read import MarkAllNotificationsReadUseCase
from tests.conftest import FakeNotificationRepo


def _n(nid, recipient="u_1", read=False):
    return Notification(
        id=nid, recipient_id=recipient, article_id="art_1", event_id="evt_1",
        type=NotificationType.REPLY, read_at=(None if not read else __import__("datetime").datetime.now(__import__("datetime").timezone.utc)),
    )


async def test_list_returns_items_with_total_and_unread():
    repo = FakeNotificationRepo([_n("ntf_1"), _n("ntf_2", read=True), _n("ntf_3", recipient="u_other")])
    uc = ListNotificationsUseCase(notification_repo=repo)
    result = await uc.execute(recipient_id="u_1", unread_only=False, page=1, limit=10)
    assert result.total == 2 and result.unread_count == 1
    assert len(result.items) == 2


async def test_list_unread_only():
    repo = FakeNotificationRepo([_n("ntf_1"), _n("ntf_2", read=True)])
    uc = ListNotificationsUseCase(notification_repo=repo)
    result = await uc.execute(recipient_id="u_1", unread_only=True, page=1, limit=10)
    assert result.total == 1 and len(result.items) == 1


async def test_mark_read():
    repo = FakeNotificationRepo([_n("ntf_1")])
    uc = MarkNotificationReadUseCase(notification_repo=repo)
    n = await uc.execute(notification_id="ntf_1", recipient_id="u_1")
    assert n is not None and n.read_at is not None


async def test_mark_read_other_users_notification_returns_none():
    repo = FakeNotificationRepo([_n("ntf_1", recipient="u_other")])
    uc = MarkNotificationReadUseCase(notification_repo=repo)
    assert await uc.execute(notification_id="ntf_1", recipient_id="u_1") is None


async def test_mark_all_read():
    repo = FakeNotificationRepo([_n("ntf_1"), _n("ntf_2")])
    uc = MarkAllNotificationsReadUseCase(notification_repo=repo)
    count = await uc.execute(recipient_id="u_1")
    assert count == 2 and await repo.count_unread("u_1") == 0
