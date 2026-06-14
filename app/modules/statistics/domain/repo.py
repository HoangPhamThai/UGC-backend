# app/modules/statistics/domain/repo.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.modules.workspaces.data.model import Article, ArticleStatus, PostMetrics, Product


@dataclass(frozen=True)
class ArticleStat:
    """Lightweight article projection carrying exactly the fields the statistics
    use cases need. `owner_user_id` is the creator, resolved by the repo via the
    article's workspace (Article has no creator_id)."""
    id: str
    name: str
    product: Product
    status: ArticleStatus
    on_air_date: date
    created_at: datetime
    owner_user_id: str
    claimed_by: Optional[str]
    reviewer_user_id: Optional[str]
    rejected_by: Optional[str]
    link: Optional[str] = None
    metrics: Optional[PostMetrics] = None


@dataclass(frozen=True)
class CreatorRef:
    id: str
    email: str


@dataclass(frozen=True)
class QcRef:
    id: str
    email: str
    products: list[Product]


class StatisticsRepo(ABC):
    """Read-only data access for statistics. Implementations do window/product
    matching and creator attribution; all counting/definition logic lives in the
    use cases."""

    @abstractmethod
    async def list_article_stats(
        self,
        *,
        from_dt: Optional[datetime],
        to_dt: Optional[datetime],
        product: Optional[Product],
        creator_id: Optional[str] = None,
        include_not_submitted: bool,
    ) -> list[ArticleStat]:
        """Articles whose created_at is within [from_dt, to_dt] (each bound
        optional/inclusive), optionally filtered by product and/or creator
        (workspace owner). When include_not_submitted is False, drafts are
        excluded."""
        ...

    @abstractmethod
    async def auto_approved_article_ids(self) -> set[str]:
        """Distinct article ids that have an AUTO_APPROVED event."""
        ...

    @abstractmethod
    async def list_creators(self, *, q: Optional[str]) -> list[CreatorRef]:
        """All active users with role=creator; when q is given, only those whose
        email contains q (case-insensitive)."""
        ...

    @abstractmethod
    async def get_creator(self, creator_id: str) -> Optional[CreatorRef]:
        """The creator with this id, or None if it does not exist or is not a
        creator."""
        ...

    @abstractmethod
    async def list_qcs(self) -> list[QcRef]:
        """All users with role=qc, with their assigned products."""
        ...

    @abstractmethod
    async def email_map(self, ids: set[str]) -> dict[str, str]:
        """Map each user id in `ids` to its email. Ids with no matching user are
        omitted from the result. Empty input returns an empty dict."""
        ...

    @abstractmethod
    async def get_article_with_owner(
        self, article_id: str
    ) -> Optional[tuple[Article, str]]:
        """The full article plus its creator (workspace owner) user id, or None if
        the article does not exist."""
        ...

    @abstractmethod
    async def feedback_counts(self, article_id: str) -> tuple[int, int]:
        """Return (anchored, general) counts of PUBLISHED feedback for the article.
        'anchored' = anchor.target_type != none; 'general' = target_type == none.
        DRAFT feedback is excluded."""
        ...
