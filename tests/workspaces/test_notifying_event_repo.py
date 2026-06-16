import pytest

from dataclasses import dataclass, field

from app.modules.notifications.data.model import NotificationType
from app.modules.workspaces.data.model import (
    Article, ArticleEvent, ArticleEventType, ArticleStatus, Workspace,
)
from app.modules.workspaces.data.notifying_event_repo import (
    NotifyingEventRepo, build_notification,
)
from tests.conftest import (
    FakeArticleEventRepo, FakeArticleRepo, FakeNotificationRepo, FakeWorkspaceRepo,
    make_article,
)


@dataclass
class FakeEmailService:
    calls: list[dict] = field(default_factory=list)

    def schedule(self, *, event_type, article, creator_user_id: str) -> None:
        self.calls.append(
            {
                "event_type": event_type,
                "article_id": article.id,
                "creator_user_id": creator_user_id,
            }
        )


def _noop_email() -> FakeEmailService:
    return FakeEmailService()


def _article(claimed_by="u_qc"):
    return make_article(status=ArticleStatus.FEEDBACK_PROVIDED, claimed_by=claimed_by)


def _event(type_, actor_id):
    return ArticleEvent(id="evt_1", article_id="art_1", actor_id=actor_id, type=type_)


# --- build_notification (pure) ---

def test_review_published_notifies_creator():
    n = build_notification(_event(ArticleEventType.REVIEW_PUBLISHED, "u_qc"),
                           _article(), owner_user_id="u_creator")
    assert n is not None and n.recipient_id == "u_creator"
    assert n.type == NotificationType.FEEDBACK_PROVIDED and n.event_id == "evt_1"
    assert n.workspace_id == "ws_1"


def test_edited_resubmitted_notifies_claiming_qc():
    n = build_notification(_event(ArticleEventType.EDITED_RESUBMITTED, "u_creator"),
                           _article(claimed_by="u_qc"), owner_user_id="u_creator")
    assert n is not None and n.recipient_id == "u_qc"
    assert n.type == NotificationType.EDITED_RESUBMITTED
    assert n.workspace_id == "ws_1"


def test_qc_reply_notifies_creator_and_creator_reply_notifies_qc():
    qc_reply = build_notification(_event(ArticleEventType.REPLY_ADDED, "u_qc"),
                                  _article(), owner_user_id="u_creator")
    assert qc_reply.recipient_id == "u_creator" and qc_reply.type == NotificationType.REPLY
    assert qc_reply.workspace_id == "ws_1"
    creator_reply = build_notification(_event(ArticleEventType.REPLY_ADDED, "u_creator"),
                                       _article(claimed_by="u_qc"), owner_user_id="u_creator")
    assert creator_reply.recipient_id == "u_qc" and creator_reply.type == NotificationType.REPLY
    assert creator_reply.workspace_id == "ws_1"


def test_non_notifying_event_returns_none():
    assert build_notification(_event(ArticleEventType.CLAIMED, "u_qc"),
                              _article(), owner_user_id="u_creator") is None


def test_no_self_notification():
    # creator-owned reply where the only candidate recipient would be the actor
    n = build_notification(_event(ArticleEventType.REPLY_ADDED, "u_creator"),
                           _article(claimed_by=None), owner_user_id="u_creator")
    assert n is None  # recipient would be claimed_by (None) -> nothing


# --- NotifyingEventRepo (integration with fakes) ---

async def test_notifying_repo_persists_event_and_notification():
    inner = FakeArticleEventRepo()
    notifs = FakeNotificationRepo()
    repo = NotifyingEventRepo(
        inner=inner, notification_repo=notifs,
        article_repo=FakeArticleRepo([_article()]),
        workspace_repo=FakeWorkspaceRepo([Workspace(id="ws_1", name="W", owner_user_id="u_creator")]),
        email_service=_noop_email(),
    )
    await repo.create(_event(ArticleEventType.APPROVED, "u_qc"))
    assert len(inner.events) == 1
    created = list(notifs.items.values())
    assert len(created) == 1 and created[0].recipient_id == "u_creator"
    assert created[0].type == NotificationType.APPROVED


async def test_notifying_repo_skips_non_notifying_event():
    inner = FakeArticleEventRepo()
    notifs = FakeNotificationRepo()
    repo = NotifyingEventRepo(
        inner=inner, notification_repo=notifs,
        article_repo=FakeArticleRepo([_article()]),
        workspace_repo=FakeWorkspaceRepo([Workspace(id="ws_1", name="W", owner_user_id="u_creator")]),
        email_service=_noop_email(),
    )
    await repo.create(_event(ArticleEventType.CLAIMED, "u_qc"))
    assert len(inner.events) == 1 and len(notifs.items) == 0


def test_rejected_notifies_creator():
    n = build_notification(_event(ArticleEventType.REJECTED, "u_qc"),
                           _article(), owner_user_id="u_creator")
    assert n is not None and n.recipient_id == "u_creator"
    assert n.type == NotificationType.REJECTED
    assert n.workspace_id == "ws_1"


async def test_notifying_repo_gracefully_skips_missing_article():
    inner = FakeArticleEventRepo()
    notifs = FakeNotificationRepo()
    repo = NotifyingEventRepo(
        inner=inner, notification_repo=notifs,
        article_repo=FakeArticleRepo([]),
        workspace_repo=FakeWorkspaceRepo([]),
        email_service=_noop_email(),
    )
    await repo.create(_event(ArticleEventType.APPROVED, "u_qc"))
    assert len(inner.events) == 1 and len(notifs.items) == 0


async def test_notifying_repo_gracefully_skips_missing_workspace():
    inner = FakeArticleEventRepo()
    notifs = FakeNotificationRepo()
    repo = NotifyingEventRepo(
        inner=inner, notification_repo=notifs,
        article_repo=FakeArticleRepo([_article()]),
        workspace_repo=FakeWorkspaceRepo([]),
        email_service=_noop_email(),
    )
    await repo.create(_event(ArticleEventType.APPROVED, "u_qc"))
    assert len(inner.events) == 1 and len(notifs.items) == 0


async def test_notifying_repo_schedules_email_for_creator_events():
    inner = FakeArticleEventRepo()
    notifs = FakeNotificationRepo()
    email_svc = FakeEmailService()
    repo = NotifyingEventRepo(
        inner=inner,
        notification_repo=notifs,
        article_repo=FakeArticleRepo([_article()]),
        workspace_repo=FakeWorkspaceRepo([Workspace(id="ws_1", name="W", owner_user_id="u_creator")]),
        email_service=email_svc,
    )
    await repo.create(_event(ArticleEventType.APPROVED, "u_qc"))
    assert len(email_svc.calls) == 1
    assert email_svc.calls[0]["creator_user_id"] == "u_creator"


async def test_notifying_repo_does_not_schedule_email_for_reply():
    inner = FakeArticleEventRepo()
    email_svc = FakeEmailService()
    repo = NotifyingEventRepo(
        inner=inner,
        notification_repo=FakeNotificationRepo(),
        article_repo=FakeArticleRepo([_article()]),
        workspace_repo=FakeWorkspaceRepo([Workspace(id="ws_1", name="W", owner_user_id="u_creator")]),
        email_service=email_svc,
    )
    await repo.create(_event(ArticleEventType.REPLY_ADDED, "u_qc"))
    assert email_svc.calls == []
