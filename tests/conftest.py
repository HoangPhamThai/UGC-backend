from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pytest

from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import (
    Article,
    ArticleEvent,
    ArticleStatus,
    Feedback,
    FeedbackReply,
    FeedbackStatus,
    Product,
    Workspace,
)
from app.modules.workspaces.domain.repo import (
    ArticleEventRepo,
    ArticleRepo,
    FeedbackRepo,
    WorkspaceRepo,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FakeWorkspaceRepo(WorkspaceRepo):
    def __init__(self, workspaces: Optional[list[Workspace]] = None) -> None:
        self.items: dict[str, Workspace] = {w.id: w for w in (workspaces or [])}

    async def create(self, workspace): self.items[workspace.id] = workspace; return workspace
    async def get_by_id(self, workspace_id): return self.items.get(workspace_id)
    async def list_by_owner(self, owner_user_id, *, skip, limit): return []
    async def count_by_owner(self, owner_user_id): return 0
    async def list_all(self, *, skip, limit): return []
    async def count_all(self): return 0
    async def list_with_products(self, products, *, skip, limit): return []
    async def count_with_products(self, products): return 0
    async def delete(self, workspace_id): self.items.pop(workspace_id, None)
    async def increment_article_count(self, workspace_id, *, by=1): ...
    async def article_counts(self, workspace_ids, *, products=None): return {}
    async def products_for(self, workspace_ids, *, restrict=None): return {}


class FakeArticleRepo(ArticleRepo):
    def __init__(self, articles: Optional[list[Article]] = None) -> None:
        self.items: dict[str, Article] = {a.id: a for a in (articles or [])}

    async def create(self, article): self.items[article.id] = article; return article
    async def get_by_id(self, article_id): return self.items.get(article_id)
    async def list_by_workspace(self, workspace_id, *, products=None): return []
    async def workspace_has_any_product(self, workspace_id, products): return False
    async def delete(self, article_id): self.items.pop(article_id, None)
    async def delete_by_workspace(self, workspace_id): return 0

    async def update_fields(self, article_id, *, name=None, product=None, on_air_date=None, content=None):
        a = self.items.get(article_id)
        if a is None:
            return None
        if name is not None: a.name = name
        if product is not None: a.product = product
        if on_air_date is not None: a.on_air_date = on_air_date
        if content is not None: a.content = content
        return a

    async def update_status(self, article_id, *, status, reviewer_user_id=None,
                            set_reviewed_at=False, last_activity_by=None,
                            increment_review_round=False):
        a = self.items.get(article_id)
        if a is None:
            return None
        a.status = status
        if reviewer_user_id is not None: a.reviewer_user_id = reviewer_user_id
        if set_reviewed_at: a.reviewed_at = _now()
        if last_activity_by is not None:
            a.last_activity_by = last_activity_by
            a.last_activity_at = _now()
        if increment_review_round: a.review_round += 1
        return a

    async def claim(self, article_id, qc_user_id):
        a = self.items.get(article_id)
        if a is None or a.claimed_by is not None:
            return None
        a.claimed_by = qc_user_id
        a.claimed_at = _now()
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
        return a


class FakeFeedbackRepo(FeedbackRepo):
    def __init__(self, feedbacks: Optional[list[Feedback]] = None) -> None:
        self.items: dict[str, Feedback] = {f.id: f for f in (feedbacks or [])}

    async def create(self, feedback): self.items[feedback.id] = feedback; return feedback
    async def get_by_id(self, feedback_id): return self.items.get(feedback_id)

    async def list_by_article(self, article_id, *, statuses=None):
        out = [f for f in self.items.values() if f.article_id == article_id]
        if statuses is not None:
            allowed = set(statuses)
            out = [f for f in out if f.status in allowed]
        return out

    async def set_status(self, feedback_id, *, status, resolved_by=None,
                         set_resolved_at=False, clear_resolved=False):
        f = self.items.get(feedback_id)
        if f is None:
            return None
        f.status = status
        if resolved_by is not None: f.resolved_by = resolved_by
        if set_resolved_at: f.resolved_at = _now()
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
            1 for f in self.items.values()
            if f.article_id == article_id and f.status == FeedbackStatus.OPEN
        )


class FakeArticleEventRepo(ArticleEventRepo):
    def __init__(self) -> None:
        self.events: list[ArticleEvent] = []

    async def create(self, event):
        self.events.append(event)
        return event


# --- Builders / fixtures ---

def make_user(role=UserRole.QC, products=None, uid="u_qc") -> User:
    qc_products = products if role == UserRole.QC else []
    if role == UserRole.QC and qc_products is None:
        qc_products = [Product.CL]
    return User(
        id=uid, email=f"{uid}@x.com", password_hashed="x", role=role,
        qc_products=qc_products or ([Product.CL] if role == UserRole.QC else []),
    )


def make_article(*, status=ArticleStatus.SUBMITTED, product=Product.CL,
                 workspace_id="ws_1", claimed_by=None, aid="art_1") -> Article:
    a = Article(
        id=aid, workspace_id=workspace_id, name="A", product=product,
        content="<p>hello world</p>", on_air_date=date.today() + timedelta(days=7),
        status=status,
    )
    a.claimed_by = claimed_by
    return a


@pytest.fixture
def qc():
    return make_user(role=UserRole.QC, products=[Product.CL], uid="u_qc")


@pytest.fixture
def creator():
    return make_user(role=UserRole.CREATOR, uid="u_creator")
