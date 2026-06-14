# app/modules/statistics/domain/usecases/get_summary.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.repo import StatisticsRepo


@dataclass(frozen=True)
class SummaryCounts:
    total: int
    awaiting_review: int
    in_review: int
    approved: int
    rejected: int
    auto_approved: int


_FINAL = (ArticleStatus.APPROVED, ArticleStatus.REJECTED)


@dataclass(frozen=True)
class GetSummaryUseCase(LoggerMixin):
    repo: StatisticsRepo

    async def execute(
        self,
        *,
        from_dt: Optional[datetime],
        to_dt: Optional[datetime],
        product: Optional[Product],
    ) -> SummaryCounts:
        stats = await self.repo.list_article_stats(
            from_dt=from_dt, to_dt=to_dt, product=product, include_not_submitted=False
        )
        auto_ids = await self.repo.auto_approved_article_ids()

        total = len(stats)
        awaiting = sum(
            1 for a in stats if a.status not in _FINAL and a.claimed_by is None
        )
        in_review = sum(
            1 for a in stats if a.status not in _FINAL and a.claimed_by is not None
        )
        rejected = sum(1 for a in stats if a.status == ArticleStatus.REJECTED)
        approved = sum(
            1 for a in stats
            if a.status == ArticleStatus.APPROVED and a.id not in auto_ids
        )
        auto_approved = sum(
            1 for a in stats
            if a.status == ArticleStatus.APPROVED and a.id in auto_ids
        )
        return SummaryCounts(
            total=total,
            awaiting_review=awaiting,
            in_review=in_review,
            approved=approved,
            rejected=rejected,
            auto_approved=auto_approved,
        )
