from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.errors import QcNotFoundError
from app.modules.statistics.domain.repo import StatisticsRepo


@dataclass(frozen=True)
class QcArticleEntry:
    id: str
    name: str
    product: Product
    status: ArticleStatus
    on_air_date: date
    created_at: datetime
    creator_email: Optional[str]
    outcome: str  # "approved" | "auto_approved" | "rejected" | "in_review"


@dataclass(frozen=True)
class QcArticlesResult:
    items: list[QcArticleEntry]
    total: int


def _outcome(status: ArticleStatus, is_auto: bool) -> str:
    if status == ArticleStatus.APPROVED:
        return "auto_approved" if is_auto else "approved"
    if status == ArticleStatus.REJECTED:
        return "rejected"
    return "in_review"


@dataclass(frozen=True)
class ListQcArticlesUseCase(LoggerMixin):
    repo: StatisticsRepo

    async def execute(
        self,
        *,
        qc_id: str,
        from_dt: Optional[datetime],
        to_dt: Optional[datetime],
        product: Optional[Product],
        page: int,
        limit: int,
    ) -> QcArticlesResult:
        qcs = await self.repo.list_qcs()
        if not any(q.id == qc_id for q in qcs):
            raise QcNotFoundError()

        stats = await self.repo.list_article_stats(
            from_dt=from_dt, to_dt=to_dt, product=product, include_not_submitted=False
        )
        claimed = [a for a in stats if a.claimed_by == qc_id]
        claimed.sort(key=lambda a: a.created_at, reverse=True)
        auto_ids = await self.repo.auto_approved_article_ids()

        total = len(claimed)
        skip = (page - 1) * limit
        page_items = claimed[skip : skip + limit]
        emails = await self.repo.email_map({a.owner_user_id for a in page_items})

        items = [
            QcArticleEntry(
                id=a.id,
                name=a.name,
                product=a.product,
                status=a.status,
                on_air_date=a.on_air_date,
                created_at=a.created_at,
                creator_email=emails.get(a.owner_user_id),
                outcome=_outcome(a.status, a.id in auto_ids),
            )
            for a in page_items
        ]
        return QcArticlesResult(items=items, total=total)
