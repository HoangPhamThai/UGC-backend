# app/modules/workspaces/domain/repo.py
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional

from app.modules.workspaces.data.model import (
    Article,
    ArticleEvent,
    ArticleStatus,
    Feedback,
    FeedbackReply,
    FeedbackStatus,
    PostMetrics,
    Product,
    Workspace,
)


class WorkspaceRepo(ABC):

    @abstractmethod
    async def create(self, workspace: Workspace) -> Workspace: ...

    @abstractmethod
    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]: ...

    @abstractmethod
    async def list_by_owner(
        self, owner_user_id: str, *, skip: int, limit: int
    ) -> list[Workspace]: ...

    @abstractmethod
    async def count_by_owner(self, owner_user_id: str) -> int: ...

    @abstractmethod
    async def list_all(self, *, skip: int, limit: int) -> list[Workspace]: ...

    @abstractmethod
    async def count_all(self) -> int: ...

    @abstractmethod
    async def list_with_products(
        self, products: list[Product], *, skip: int, limit: int
    ) -> list[Workspace]: ...

    @abstractmethod
    async def count_with_products(self, products: list[Product]) -> int: ...

    @abstractmethod
    async def delete(self, workspace_id: str) -> None: ...

    @abstractmethod
    async def increment_article_count(
        self, workspace_id: str, *, by: int = 1
    ) -> None: ...

    @abstractmethod
    async def article_counts(
        self, workspace_ids: list[str], *, products: Optional[list[Product]] = None
    ) -> dict[str, int]: ...

    @abstractmethod
    async def products_for(
        self, workspace_ids: list[str], *, restrict: Optional[list[Product]] = None
    ) -> dict[str, list[Product]]:
        """Distinct products per workspace. When `restrict` is given, only those
        products are considered (used to scope a QC to its assigned products)."""
        ...


class ArticleRepo(ABC):

    @abstractmethod
    async def create(self, article: Article) -> Article: ...

    @abstractmethod
    async def get_by_id(self, article_id: str) -> Optional[Article]: ...

    @abstractmethod
    async def list_by_workspace(
        self, workspace_id: str, *, products: Optional[list[Product]] = None
    ) -> list[Article]: ...

    @abstractmethod
    async def workspace_has_any_product(
        self, workspace_id: str, products: list[Product]
    ) -> bool: ...

    @abstractmethod
    async def update_fields(
        self,
        article_id: str,
        *,
        name: Optional[str] = None,
        product: Optional[Product] = None,
        on_air_date: Optional[date] = None,
        content: Optional[str] = None,
    ) -> Optional[Article]:
        """Set any provided subset of editable fields; bumps updated_at.

        `content` is distinguished from "not provided" by being non-None, so an
        empty string clears the content (articles may be empty)."""
        ...

    @abstractmethod
    async def set_link(
        self, article_id: str, *, link: str, link_edit_count: int
    ) -> Optional[Article]:
        """Set link + link_submitted_at(now) + link_edit_count; bumps updated_at.
        Also RESETS extraction state (status=pending, metrics=None, error=None,
        attempts=0, extracted_at=None) since a new link must be re-extracted.
        Returns the updated Article, or None if not found."""
        ...

    @abstractmethod
    async def record_extraction_success(
        self, article_id: str, *, url: str, metrics: "PostMetrics"
    ) -> Optional[Article]:
        """Store metrics + status=extracted + extracted_at(now), clear error —
        ONLY if the article's current link still equals `url` (else no-op/None,
        guarding against a stale extraction overwriting a newer link)."""
        ...

    @abstractmethod
    async def record_extraction_failure(
        self, article_id: str, *, url: str, error: str
    ) -> Optional[Article]:
        """Set status=failed + error, increment extraction_attempts — ONLY if the
        article's current link still equals `url` (else no-op/None)."""
        ...

    @abstractmethod
    async def set_extraction_pending(self, article_id: str) -> Optional[Article]:
        """Reset status=pending + clear error (used by the retry endpoint)."""
        ...

    @abstractmethod
    async def update_status(
        self,
        article_id: str,
        *,
        status: ArticleStatus,
        reviewer_user_id: Optional[str] = None,
        set_reviewed_at: bool = False,
        last_activity_by: Optional[str] = None,
        increment_review_round: bool = False,
        reviewed_content: Optional[str] = None,
        clear_reviewed_content: bool = False,
    ) -> Optional[Article]: ...

    @abstractmethod
    async def claim(self, article_id: str, qc_user_id: str) -> Optional[Article]:
        """Atomically set claimed_by/claimed_at only if currently unclaimed.
        Returns the updated Article, or None if not found OR already claimed."""
        ...

    @abstractmethod
    async def withdraw(self, article_id: str, *, actor_id: str) -> Optional[Article]:
        """Atomically flip submitted -> not_submitted only if currently SUBMITTED
        AND unclaimed (claimed_by is null). Sets last_activity. Returns the updated
        Article, or None if the precondition no longer holds (lost to a concurrent claim).
        """
        ...

    @abstractmethod
    async def touch_activity(self, article_id: str, *, actor_id: str) -> None:
        """Set last_activity_by/last_activity_at = (actor_id, now). No status change."""
        ...

    @abstractmethod
    async def reject(
        self, article_id: str, *, reviewer_user_id: str, reason: str
    ) -> Optional[Article]:
        """Set status=rejected and all reject bookkeeping fields atomically."""
        ...

    @abstractmethod
    async def list_by_products(
        self,
        products: Optional[list[Product]],
        *,
        statuses: Optional[list[ArticleStatus]],
        skip: int,
        limit: int,
    ) -> list[Article]:
        """Articles whose product is in `products` (None = all products), optionally
        filtered by `statuses`, sorted by on_air_date ascending then created_at."""
        ...

    @abstractmethod
    async def count_by_products(
        self,
        products: Optional[list[Product]],
        *,
        statuses: Optional[list[ArticleStatus]],
    ) -> int: ...

    @abstractmethod
    async def delete(self, article_id: str) -> None: ...

    @abstractmethod
    async def delete_by_workspace(self, workspace_id: str) -> int: ...


class FeedbackRepo(ABC):

    @abstractmethod
    async def create(self, feedback: Feedback) -> Feedback: ...

    @abstractmethod
    async def get_by_id(self, feedback_id: str) -> Optional[Feedback]: ...

    @abstractmethod
    async def list_by_article(
        self, article_id: str, *, statuses: Optional[list[FeedbackStatus]] = None
    ) -> list[Feedback]: ...

    @abstractmethod
    async def set_status(
        self,
        feedback_id: str,
        *,
        status: FeedbackStatus,
        resolved_by: Optional[str] = None,
        set_resolved_at: bool = False,
        clear_resolved: bool = False,
    ) -> Optional[Feedback]:
        """Update a feedback's status. `clear_resolved` wipes resolved_by/at (used on reopen)."""
        ...

    @abstractmethod
    async def mark_drafts_open(self, article_id: str) -> int:
        """Flip every DRAFT feedback of the article to OPEN. Returns count flipped."""
        ...

    @abstractmethod
    async def add_reply(
        self, feedback_id: str, reply: FeedbackReply
    ) -> Optional[Feedback]: ...

    @abstractmethod
    async def count_open(self, article_id: str) -> int:
        """Number of feedbacks in OPEN status for the article."""
        ...

    @abstractmethod
    async def update_body(self, feedback_id: str, body: str) -> Optional[Feedback]: ...

    @abstractmethod
    async def delete(self, feedback_id: str) -> bool: ...


class ArticleEventRepo(ABC):

    @abstractmethod
    async def create(self, event: ArticleEvent) -> ArticleEvent: ...
