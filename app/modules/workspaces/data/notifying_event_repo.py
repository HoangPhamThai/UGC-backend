# app/modules/workspaces/data/notifying_event_repo.py
from dataclasses import dataclass
from typing import Optional

from app.modules.notifications.data.model import Notification, NotificationType
from app.modules.notifications.domain.repo import NotificationRepo
from app.modules.workspaces.data.model import Article, ArticleEvent, ArticleEventType
from app.modules.workspaces.domain.repo import ArticleEventRepo, ArticleRepo, WorkspaceRepo

NOTIFYING_EVENT_TYPES: frozenset[ArticleEventType] = frozenset({
    ArticleEventType.REVIEW_PUBLISHED,
    ArticleEventType.APPROVED,
    ArticleEventType.REJECTED,
    ArticleEventType.EDITED_RESUBMITTED,
    ArticleEventType.REPLY_ADDED,
})

# Events that always notify the creator (workspace owner).
_TO_CREATOR: dict[ArticleEventType, NotificationType] = {
    ArticleEventType.REVIEW_PUBLISHED: NotificationType.FEEDBACK_PROVIDED,
    ArticleEventType.APPROVED: NotificationType.APPROVED,
    ArticleEventType.REJECTED: NotificationType.REJECTED,
}


def build_notification(
    event: ArticleEvent, article: Article, owner_user_id: str
) -> Optional[Notification]:
    """Pure mapping from an article event to the notification it should produce
    (or None). See qc-review.md §8.2."""
    recipient: Optional[str] = None
    ntype: Optional[NotificationType] = None

    if event.type in _TO_CREATOR:
        recipient, ntype = owner_user_id, _TO_CREATOR[event.type]
    elif event.type == ArticleEventType.EDITED_RESUBMITTED:
        recipient, ntype = article.claimed_by, NotificationType.EDITED_RESUBMITTED
    elif event.type == ArticleEventType.REPLY_ADDED:
        ntype = NotificationType.REPLY
        # Notify the other party in the thread.
        recipient = article.claimed_by if event.actor_id == owner_user_id else owner_user_id
    else:
        return None

    if not recipient or recipient == event.actor_id:
        return None
    return Notification(
        recipient_id=recipient, article_id=event.article_id,
        event_id=event.id, type=ntype,
    )


@dataclass(frozen=True)
class NotifyingEventRepo(ArticleEventRepo):
    """Decorator over an ArticleEventRepo: persists the event, then fans out a
    notification for notifying event types. No-op (just persists) otherwise."""
    inner: ArticleEventRepo
    notification_repo: NotificationRepo
    article_repo: ArticleRepo
    workspace_repo: WorkspaceRepo

    async def create(self, event: ArticleEvent) -> ArticleEvent:
        await self.inner.create(event)
        if event.type not in NOTIFYING_EVENT_TYPES:
            return event
        article = await self.article_repo.get_by_id(event.article_id)
        if article is None:
            return event
        ws = await self.workspace_repo.get_by_id(article.workspace_id)
        if ws is None:
            return event
        notification = build_notification(event, article, ws.owner_user_id)
        if notification is not None:
            await self.notification_repo.create(notification)
        return event
