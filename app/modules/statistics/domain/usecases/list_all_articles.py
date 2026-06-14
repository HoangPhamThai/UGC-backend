from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import ArticleStatus, PostMetrics, Product
from app.modules.statistics.domain.repo import StatisticsRepo


@dataclass(frozen=True)
class ArticleRowEntry:
    id: str
    name: str
    product: Product
    status: ArticleStatus
    on_air_date: date
    created_at: datetime
    creator_email: Optional[str]
    claimed_by_email: Optional[str]
    reviewer_email: Optional[str]
    link: Optional[str] = None
    metrics: Optional[PostMetrics] = None


@dataclass(frozen=True)
class ArticleListResult:
    items: list[ArticleRowEntry]
    total: int


def _views(stat) -> Optional[int]:
    return stat.metrics.views if stat.metrics else None


@dataclass(frozen=True)
class ListAllArticlesUseCase(LoggerMixin):
    repo: StatisticsRepo

    async def execute(
        self,
        *,
        from_dt: Optional[datetime],
        to_dt: Optional[datetime],
        product: Optional[Product],
        page: int,
        limit: int,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> ArticleListResult:
        stats = await self.repo.list_article_stats(
            from_dt=from_dt, to_dt=to_dt, product=product, include_not_submitted=False
        )

        reverse = order == "desc"
        if sort_by == "views":
            # Articles without a view count always sort last, regardless of order.
            present = [a for a in stats if _views(a) is not None]
            absent = [a for a in stats if _views(a) is None]
            present.sort(key=_views, reverse=reverse)
            stats = present + absent
        elif sort_by == "on_air_date":
            stats.sort(key=lambda a: a.on_air_date, reverse=reverse)
        else:  # "created_at"
            stats.sort(key=lambda a: a.created_at, reverse=reverse)

        total = len(stats)
        skip = (page - 1) * limit
        page_items = stats[skip : skip + limit]

        ids: set[str] = set()
        for a in page_items:
            ids.add(a.owner_user_id)
            if a.claimed_by:
                ids.add(a.claimed_by)
            if a.reviewer_user_id:
                ids.add(a.reviewer_user_id)
        emails = await self.repo.email_map(ids)

        items = [
            ArticleRowEntry(
                id=a.id,
                name=a.name,
                product=a.product,
                status=a.status,
                on_air_date=a.on_air_date,
                created_at=a.created_at,
                creator_email=emails.get(a.owner_user_id),
                claimed_by_email=emails.get(a.claimed_by) if a.claimed_by else None,
                reviewer_email=emails.get(a.reviewer_user_id) if a.reviewer_user_id else None,
                link=a.link,
                metrics=a.metrics,
            )
            for a in page_items
        ]
        return ArticleListResult(items=items, total=total)
