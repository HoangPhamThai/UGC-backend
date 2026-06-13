# app/modules/statistics/domain/usecases/get_qc_breakdown.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.repo import StatisticsRepo


@dataclass(frozen=True)
class QcBreakdownRow:
    qc_id: str
    email: str
    products: list[Product]
    claimed: int
    approved: int
    rejected: int
    auto_approved_after_claim: int


@dataclass(frozen=True)
class QcBreakdownResult:
    items: list[QcBreakdownRow]


@dataclass(frozen=True)
class GetQcBreakdownUseCase(LoggerMixin):
    repo: StatisticsRepo

    async def execute(
        self,
        *,
        from_dt: Optional[datetime],
        to_dt: Optional[datetime],
        product: Optional[Product],
    ) -> QcBreakdownResult:
        qcs = await self.repo.list_qcs()
        stats = await self.repo.list_article_stats(
            from_dt=from_dt, to_dt=to_dt, product=product, include_not_submitted=False
        )
        auto_ids = await self.repo.auto_approved_article_ids()

        rows: list[QcBreakdownRow] = []
        for qc in qcs:
            claimed = sum(1 for a in stats if a.claimed_by == qc.id)
            approved = sum(
                1 for a in stats
                if a.reviewer_user_id == qc.id
                and a.status == ArticleStatus.APPROVED
                and a.id not in auto_ids
            )
            rejected = sum(
                1 for a in stats
                if a.rejected_by == qc.id and a.status == ArticleStatus.REJECTED
            )
            auto_after_claim = sum(
                1 for a in stats if a.claimed_by == qc.id and a.id in auto_ids
            )
            rows.append(
                QcBreakdownRow(
                    qc_id=qc.id,
                    email=qc.email,
                    products=list(qc.products),
                    claimed=claimed,
                    approved=approved,
                    rejected=rejected,
                    auto_approved_after_claim=auto_after_claim,
                )
            )
        return QcBreakdownResult(items=rows)
