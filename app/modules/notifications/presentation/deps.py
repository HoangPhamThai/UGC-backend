# app/modules/notifications/presentation/deps.py
from functools import lru_cache

from app.modules.notifications.data.repo import NotificationDataRepository
from app.modules.notifications.domain.repo import NotificationRepo
from app.modules.notifications.domain.usecases.list_notifications import ListNotificationsUseCase
from app.modules.notifications.domain.usecases.mark_all_notifications_read import MarkAllNotificationsReadUseCase
from app.modules.notifications.domain.usecases.mark_notification_read import MarkNotificationReadUseCase


@lru_cache(maxsize=1)
def get_notification_repo() -> NotificationRepo:
    return NotificationDataRepository()


def get_uc_list_notifications() -> ListNotificationsUseCase:
    return ListNotificationsUseCase(notification_repo=get_notification_repo())


def get_uc_mark_notification_read() -> MarkNotificationReadUseCase:
    return MarkNotificationReadUseCase(notification_repo=get_notification_repo())


def get_uc_mark_all_notifications_read() -> MarkAllNotificationsReadUseCase:
    return MarkAllNotificationsReadUseCase(notification_repo=get_notification_repo())
