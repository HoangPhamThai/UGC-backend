from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pytest

from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import (
    Article,
    ArticleEvent,
    ArticleStatus,
    AWAITING_QC_STATUSES,
    ExtractionStatus,
    Feedback,
    FeedbackReply,
    FeedbackStatus,
    PostMetrics,
    Product,
    Workspace,
)
from app.modules.notifications.data.model import Notification
from app.modules.notifications.domain.repo import NotificationRepo
from app.modules.statistics.domain.repo import (
    ArticleStat,
    CreatorRef,
    QcRef,
    StatisticsRepo,
)
from app.modules.workspaces.domain.repo import (
    ArticleEventRepo,
    ArticleRepo,
    FeedbackRepo,
    WorkspaceRepo,
)
from app.modules.interim_keys.data.model import InterimKey
from app.modules.interim_keys.domain.repo import InterimKeyRepo
from app.modules.chat.data.model import ChatMessage, ChatRole, ChatSession
from app.modules.chat.domain.repo import ChatSessionRepo, ChatSessionSummary


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FakeWorkspaceRepo(WorkspaceRepo):
    def __init__(self, workspaces: Optional[list[Workspace]] = None) -> None:
        self.items: dict[str, Workspace] = {w.id: w for w in (workspaces or [])}

    async def create(self, workspace):
        self.items[workspace.id] = workspace
        return workspace

    async def get_by_id(self, workspace_id):
        return self.items.get(workspace_id)

    async def list_by_owner(self, owner_user_id, *, skip, limit):
        return []

    async def count_by_owner(self, owner_user_id):
        return 0

    async def list_all(self, *, skip, limit):
        return []

    async def count_all(self):
        return 0

    async def list_with_products(self, products, *, skip, limit):
        return []

    async def count_with_products(self, products):
        return 0

    async def delete(self, workspace_id):
        self.items.pop(workspace_id, None)

    async def increment_article_count(self, workspace_id, *, by=1): ...
    async def article_counts(self, workspace_ids, *, products=None):
        return {}

    async def products_for(self, workspace_ids, *, restrict=None):
        return {}


class FakeArticleRepo(ArticleRepo):
    def __init__(self, articles: Optional[list[Article]] = None) -> None:
        self.items: dict[str, Article] = {a.id: a for a in (articles or [])}

    async def create(self, article):
        self.items[article.id] = article
        return article

    async def get_by_id(self, article_id):
        return self.items.get(article_id)

    async def list_by_workspace(self, workspace_id, *, products=None):
        return []

    async def workspace_has_any_product(self, workspace_id, products):
        return False

    async def delete(self, article_id):
        self.items.pop(article_id, None)

    async def delete_by_workspace(self, workspace_id):
        return 0

    async def update_fields(
        self, article_id, *, name=None, product=None, on_air_date=None, content=None
    ):
        a = self.items.get(article_id)
        if a is None:
            return None
        if name is not None:
            a.name = name
        if product is not None:
            a.product = product
        if on_air_date is not None:
            a.on_air_date = on_air_date
        if content is not None:
            a.content = content
        return a

    async def set_link(self, article_id, *, link, link_edit_count):
        a = self.items.get(article_id)
        if a is None:
            return None
        a.link = link
        a.link_submitted_at = _now()
        a.link_edit_count = link_edit_count
        a.extraction_status = ExtractionStatus.PENDING
        a.extraction_error = None
        a.extraction_attempts = 0
        a.extracted_at = None
        a.metrics = None
        return a

    async def set_report_id(self, article_id, report_id):
        a = self.items.get(article_id)
        if a is None:
            return None
        a.report_id = report_id
        return a

    async def record_extraction_success(self, article_id, *, url, metrics):
        a = self.items.get(article_id)
        if a is None or a.link != url:
            return None
        a.metrics = metrics
        a.extraction_status = ExtractionStatus.EXTRACTED
        a.extracted_at = _now()
        a.extraction_error = None
        return a

    async def record_extraction_failure(self, article_id, *, url, error):
        a = self.items.get(article_id)
        if a is None or a.link != url:
            return None
        a.extraction_status = ExtractionStatus.FAILED
        a.extraction_error = error
        a.extraction_attempts += 1
        return a

    async def set_extraction_pending(self, article_id):
        a = self.items.get(article_id)
        if a is None:
            return None
        a.extraction_status = ExtractionStatus.PENDING
        a.extraction_error = None
        return a

    async def update_status(
        self,
        article_id,
        *,
        status,
        reviewer_user_id=None,
        set_reviewed_at=False,
        last_activity_by=None,
        increment_review_round=False,
        reviewed_content=None,
        clear_reviewed_content=False,
    ):
        a = self.items.get(article_id)
        if a is None:
            return None
        a.status = status
        if reviewer_user_id is not None:
            a.reviewer_user_id = reviewer_user_id
        if set_reviewed_at:
            a.reviewed_at = _now()
        if last_activity_by is not None:
            a.last_activity_by = last_activity_by
            a.last_activity_at = _now()
        if increment_review_round:
            a.review_round += 1
        if clear_reviewed_content:
            a.reviewed_content = None
        elif reviewed_content is not None:
            a.reviewed_content = reviewed_content
        return a

    async def claim(self, article_id, qc_user_id):
        a = self.items.get(article_id)
        if (
            a is None
            or a.claimed_by is not None
            or a.status not in AWAITING_QC_STATUSES
        ):
            return None
        a.claimed_by = qc_user_id
        a.claimed_at = _now()
        return a

    async def withdraw(self, article_id, *, actor_id):
        a = self.items.get(article_id)
        if a is None or a.status != ArticleStatus.SUBMITTED or a.claimed_by is not None:
            return None
        a.status = ArticleStatus.NOT_SUBMITTED
        a.last_activity_by = actor_id
        a.last_activity_at = _now()
        return a

    async def touch_activity(self, article_id, *, actor_id):
        a = self.items.get(article_id)
        if a is not None:
            a.last_activity_by = actor_id
            a.last_activity_at = _now()

    async def reject(self, article_id, *, reviewer_user_id, reason):
        a = self.items.get(article_id)
        if a is None:
            return None
        a.status = ArticleStatus.REJECTED
        a.reviewer_user_id = reviewer_user_id
        a.reviewed_at = _now()
        a.reject_reason = reason
        a.rejected_by = reviewer_user_id
        a.rejected_at = _now()
        a.last_activity_by = reviewer_user_id
        a.last_activity_at = _now()
        a.reviewed_content = None
        return a

    async def list_by_products(self, products, *, statuses, skip, limit):
        rows = [
            a
            for a in self.items.values()
            if (products is None or a.product in products)
            and (statuses is None or a.status in statuses)
        ]
        rows.sort(key=lambda a: (a.on_air_date, a.created_at))
        return rows[skip : skip + limit]

    async def count_by_products(self, products, *, statuses):
        return sum(
            1
            for a in self.items.values()
            if (products is None or a.product in products)
            and (statuses is None or a.status in statuses)
        )


class FakeFeedbackRepo(FeedbackRepo):
    def __init__(self, feedbacks: Optional[list[Feedback]] = None) -> None:
        self.items: dict[str, Feedback] = {f.id: f for f in (feedbacks or [])}

    async def create(self, feedback):
        self.items[feedback.id] = feedback
        return feedback

    async def get_by_id(self, feedback_id):
        return self.items.get(feedback_id)

    async def list_by_article(self, article_id, *, statuses=None):
        out = [f for f in self.items.values() if f.article_id == article_id]
        if statuses is not None:
            allowed = set(statuses)
            out = [f for f in out if f.status in allowed]
        return out

    async def set_status(
        self,
        feedback_id,
        *,
        status,
        resolved_by=None,
        set_resolved_at=False,
        clear_resolved=False,
    ):
        f = self.items.get(feedback_id)
        if f is None:
            return None
        f.status = status
        if resolved_by is not None:
            f.resolved_by = resolved_by
        if set_resolved_at:
            f.resolved_at = _now()
        if clear_resolved:
            f.resolved_by = None
            f.resolved_at = None
        return f

    async def mark_drafts_open(self, article_id):
        n = 0
        for f in self.items.values():
            if f.article_id == article_id and f.status == FeedbackStatus.DRAFT:
                f.status = FeedbackStatus.OPEN
                n += 1
        return n

    async def add_reply(self, feedback_id, reply):
        f = self.items.get(feedback_id)
        if f is None:
            return None
        f.replies.append(reply)
        return f

    async def count_open(self, article_id):
        return sum(
            1
            for f in self.items.values()
            if f.article_id == article_id and f.status == FeedbackStatus.OPEN
        )

    async def update_body(self, feedback_id: str, body: str) -> Optional[Feedback]:
        f = self.items.get(feedback_id)
        if f is None:
            return None
        f.body = body
        return f

    async def delete(self, feedback_id: str) -> bool:
        if feedback_id not in self.items:
            return False
        del self.items[feedback_id]
        return True


class FakeArticleEventRepo(ArticleEventRepo):
    def __init__(self) -> None:
        self.events: list[ArticleEvent] = []

    async def create(self, event):
        self.events.append(event)
        return event


class FakeNotificationRepo(NotificationRepo):
    def __init__(self, items: Optional[list[Notification]] = None) -> None:
        self.items: dict[str, Notification] = {n.id: n for n in (items or [])}

    async def create(self, notification):
        self.items[notification.id] = notification
        return notification

    def _matches(self, n, recipient_id, unread_only):
        return n.recipient_id == recipient_id and (not unread_only or n.read_at is None)

    async def list_for_recipient(self, recipient_id, *, unread_only, skip, limit):
        rows = [
            n
            for n in self.items.values()
            if self._matches(n, recipient_id, unread_only)
        ]
        rows.sort(key=lambda n: n.created_at, reverse=True)
        return rows[skip : skip + limit]

    async def count_for_recipient(self, recipient_id, *, unread_only):
        return sum(
            1
            for n in self.items.values()
            if self._matches(n, recipient_id, unread_only)
        )

    async def mark_read(self, notification_id, recipient_id):
        n = self.items.get(notification_id)
        if n is None or n.recipient_id != recipient_id:
            return None
        if n.read_at is None:
            n.read_at = _now()
        return n

    async def mark_all_read(self, recipient_id):
        c = 0
        for n in self.items.values():
            if n.recipient_id == recipient_id and n.read_at is None:
                n.read_at = _now()
                c += 1
        return c


class FakeStatisticsRepo(StatisticsRepo):
    def __init__(
        self,
        *,
        stats: Optional[list[ArticleStat]] = None,
        auto_ids: Optional[set[str]] = None,
        creators: Optional[list[CreatorRef]] = None,
        qcs: Optional[list[QcRef]] = None,
        emails: Optional[dict[str, str]] = None,
        details: Optional[dict] = None,        # article_id -> (Article, owner_user_id)
        fb_counts: Optional[dict] = None,       # article_id -> (anchored, general)
    ) -> None:
        self._stats = list(stats or [])
        self._auto = set(auto_ids or set())
        self._creators = list(creators or [])
        self._qcs = list(qcs or [])
        self._emails = dict(emails or {})
        self._details = dict(details or {})
        self._fb_counts = dict(fb_counts or {})

    async def list_article_stats(
        self,
        *,
        from_dt=None,
        to_dt=None,
        product=None,
        creator_id=None,
        include_not_submitted,
    ):
        out = []
        for a in self._stats:
            if from_dt is not None and a.created_at < from_dt:
                continue
            if to_dt is not None and a.created_at > to_dt:
                continue
            if product is not None and a.product != product:
                continue
            if creator_id is not None and a.owner_user_id != creator_id:
                continue
            if not include_not_submitted and a.status == ArticleStatus.NOT_SUBMITTED:
                continue
            out.append(a)
        return out

    async def auto_approved_article_ids(self):
        return set(self._auto)

    async def list_creators(self, *, q):
        return [
            c for c in self._creators
            if q is None or q.lower() in c.email.lower()
        ]

    async def get_creator(self, creator_id):
        return next((c for c in self._creators if c.id == creator_id), None)

    async def list_qcs(self):
        return list(self._qcs)

    async def email_map(self, ids):
        return {uid: self._emails[uid] for uid in ids if uid in self._emails}

    async def get_article_with_owner(self, article_id):
        return self._details.get(article_id)

    async def feedback_counts(self, article_id):
        return self._fb_counts.get(article_id, (0, 0))


class FakeInterimKeyRepo(InterimKeyRepo):
    def __init__(self, keys: Optional[list[InterimKey]] = None) -> None:
        self.items: dict[str, InterimKey] = {k.id: k for k in (keys or [])}

    async def create(self, key):
        self.items[key.id] = key
        return key

    async def get_active_by_hash(self, key_hash, now):
        for k in self.items.values():
            if k.key_hash == key_hash and k.expires_at > now:
                return k
        return None

    async def delete_by_hash(self, key_hash) -> bool:
        match = [kid for kid, k in self.items.items() if k.key_hash == key_hash]
        for kid in match:
            del self.items[kid]
        return bool(match)


def make_article_stat(
    *,
    aid="art_1",
    name="A",
    product=Product.CL,
    status=ArticleStatus.SUBMITTED,
    owner_user_id="u_creator",
    claimed_by=None,
    reviewer_user_id=None,
    rejected_by=None,
    created_at=None,
    on_air_date=None,
    link=None,
    metrics=None,
) -> ArticleStat:
    return ArticleStat(
        id=aid,
        name=name,
        product=product,
        status=status,
        on_air_date=on_air_date or (date.today() + timedelta(days=7)),
        created_at=created_at or _now(),
        owner_user_id=owner_user_id,
        claimed_by=claimed_by,
        reviewer_user_id=reviewer_user_id,
        rejected_by=rejected_by,
        link=link,
        metrics=metrics,
    )


class FakeChatSessionRepo(ChatSessionRepo):
    def __init__(self, sessions: Optional[list[ChatSession]] = None) -> None:
        self.items: dict[str, ChatSession] = {s.id: s for s in (sessions or [])}

    async def create(self, session):
        self.items[session.id] = session
        return session

    async def get_by_id(self, session_id):
        return self.items.get(session_id)

    async def list_summaries_by_owner(self, user_id, *, skip, limit):
        owned = [s for s in self.items.values() if s.user_id == user_id]
        owned.sort(key=lambda s: s.updated_at, reverse=True)
        page = owned[skip : skip + limit]
        return [
            ChatSessionSummary(
                id=s.id,
                title=s.title,
                message_count=len(s.messages),
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in page
        ]

    async def count_by_owner(self, user_id):
        return sum(1 for s in self.items.values() if s.user_id == user_id)

    async def delete(self, session_id):
        self.items.pop(session_id, None)

    async def append_messages(self, session_id, messages, *, title):
        s = self.items.get(session_id)
        if s is None:
            return None
        s.messages.extend(messages)
        if title is not None:
            s.title = title
        s.updated_at = _now()
        return s

    async def clear_messages(self, session_id):
        s = self.items.get(session_id)
        if s is None:
            return None
        s.messages = []
        s.updated_at = _now()
        return s


# --- Builders / fixtures ---


def make_user(role=UserRole.QC, products=None, uid="u_qc") -> User:
    if role == UserRole.QC:
        qc_products = products if products is not None else [Product.CL]
    else:
        qc_products = []
    return User(
        id=uid,
        email=f"{uid}@x.com",
        password_hashed="x",
        role=role,
        qc_products=qc_products,
    )


def make_article(
    *,
    status=ArticleStatus.SUBMITTED,
    product=Product.CL,
    workspace_id="ws_1",
    claimed_by=None,
    aid="art_1",
) -> Article:
    return Article(
        id=aid,
        workspace_id=workspace_id,
        name="A",
        product=product,
        content="<p>hello world</p>",
        on_air_date=date.today() + timedelta(days=7),
        status=status,
        claimed_by=claimed_by,
    )


def make_chat_session(*, sid="cs_1", user_id="u_admin", title="", messages=None) -> ChatSession:
    return ChatSession(
        id=sid, user_id=user_id, title=title, messages=messages or []
    )


@pytest.fixture
def qc():
    return make_user(role=UserRole.QC, products=[Product.CL], uid="u_qc")


@pytest.fixture
def creator():
    return make_user(role=UserRole.CREATOR, uid="u_creator")
