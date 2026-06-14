# app/modules/statistics/domain/usecases/list_creator_articles.py
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.errors import CreatorNotFoundError
from app.modules.statistics.domain.repo import StatisticsRepo


@dataclass(frozen=True)
class CreatorArticleEntry:
    id: str
    name: str
    product: Product
    status: ArticleStatus
    on_air_date: date
    created_at: datetime
    claimed_by: Optional[str]
    reviewer_user_id: Optional[str]
    claimed_by_email: Optional[str]
    reviewer_email: Optional[str]


@dataclass(frozen=True)
class CreatorArticlesResult:
    items: list[CreatorArticleEntry]
    total: int


@dataclass(frozen=True)
class ListCreatorArticlesUseCase(LoggerMixin):
    repo: StatisticsRepo

    async def execute(
        self,
        *,
        creator_id: str,
        from_dt: Optional[datetime],
        to_dt: Optional[datetime],
        product: Optional[Product],
        page: int,
        limit: int,
    ) -> CreatorArticlesResult:
        creator = await self.repo.get_creator(creator_id)
        if creator is None:
            raise CreatorNotFoundError()

        stats = await self.repo.list_article_stats(
            from_dt=from_dt,
            to_dt=to_dt,
            product=product,
            creator_id=creator_id,
            include_not_submitted=True,
        )
        stats.sort(key=lambda a: a.created_at, reverse=True)

        total = len(stats)
        skip = (page - 1) * limit
        page_items = stats[skip : skip + limit]

        ids: set[str] = set()
        for a in page_items:
            if a.claimed_by:
                ids.add(a.claimed_by)
            if a.reviewer_user_id:
                ids.add(a.reviewer_user_id)
        emails = await self.repo.email_map(ids)

        items = [
            CreatorArticleEntry(
                id=a.id,
                name=a.name,
                product=a.product,
                status=a.status,
                on_air_date=a.on_air_date,
                created_at=a.created_at,
                claimed_by=a.claimed_by,
                reviewer_user_id=a.reviewer_user_id,
                claimed_by_email=emails.get(a.claimed_by) if a.claimed_by else None,
                reviewer_email=emails.get(a.reviewer_user_id) if a.reviewer_user_id else None,
            )
            for a in page_items
        ]
        return CreatorArticlesResult(items=items, total=total)
