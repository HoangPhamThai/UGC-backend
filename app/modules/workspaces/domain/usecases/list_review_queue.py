# app/modules/workspaces/domain/usecases/list_review_queue.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import Article, ArticleStatus, Product
from app.modules.workspaces.domain.errors import QcMisconfiguredError
from app.modules.workspaces.domain.repo import ArticleRepo


class ReviewQueueGroup(str, Enum):
    NEEDS_REVIEW = "needs_review"
    WAITING_CREATOR = "waiting_creator"
    DONE = "done"


_GROUP_STATUSES: dict[ReviewQueueGroup, list[ArticleStatus]] = {
    ReviewQueueGroup.NEEDS_REVIEW: [ArticleStatus.SUBMITTED, ArticleStatus.EDITED],
    ReviewQueueGroup.WAITING_CREATOR: [ArticleStatus.FEEDBACK_PROVIDED],
    ReviewQueueGroup.DONE: [ArticleStatus.APPROVED, ArticleStatus.REJECTED],
}


@dataclass(frozen=True)
class ReviewQueueResult:
    items: list[Article]
    total: int


@dataclass(frozen=True)
class ListReviewQueueUseCase(LoggerMixin):
    article_repo: ArticleRepo

    async def execute(
        self, *, caller: User, group: ReviewQueueGroup, page: int, limit: int
    ) -> ReviewQueueResult:
        if caller.role == UserRole.SUPERUSER:
            products: Optional[list[Product]] = None  # all products
        else:
            if not caller.qc_products:
                raise QcMisconfiguredError()
            products = list(caller.qc_products)

        statuses = _GROUP_STATUSES[group]
        skip = (page - 1) * limit
        items = await self.article_repo.list_by_products(
            products, statuses=statuses, skip=skip, limit=limit
        )
        total = await self.article_repo.count_by_products(products, statuses=statuses)
        return ReviewQueueResult(items=items, total=total)
