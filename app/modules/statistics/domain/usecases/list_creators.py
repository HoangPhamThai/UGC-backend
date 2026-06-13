# app/modules/statistics/domain/usecases/list_creators.py
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import Product
from app.modules.statistics.domain.repo import StatisticsRepo


@dataclass(frozen=True)
class CreatorListEntry:
    id: str
    email: str
    article_count_in_window: int


@dataclass(frozen=True)
class CreatorListResult:
    items: list[CreatorListEntry]
    total: int


@dataclass(frozen=True)
class ListCreatorsUseCase(LoggerMixin):
    repo: StatisticsRepo

    async def execute(
        self,
        *,
        q: Optional[str],
        from_dt: Optional[datetime],
        to_dt: Optional[datetime],
        product: Optional[Product],
        page: int,
        limit: int,
    ) -> CreatorListResult:
        creators = await self.repo.list_creators(q=q)
        # Non-draft article counts per creator within the same window/product.
        stats = await self.repo.list_article_stats(
            from_dt=from_dt, to_dt=to_dt, product=product, include_not_submitted=False
        )
        counts = Counter(a.owner_user_id for a in stats)

        time_filter_active = from_dt is not None or to_dt is not None

        entries = [
            CreatorListEntry(
                id=c.id, email=c.email, article_count_in_window=counts.get(c.id, 0)
            )
            for c in creators
            if not time_filter_active or counts.get(c.id, 0) > 0
        ]
        entries.sort(key=lambda e: e.email)

        total = len(entries)
        skip = (page - 1) * limit
        return CreatorListResult(items=entries[skip : skip + limit], total=total)
