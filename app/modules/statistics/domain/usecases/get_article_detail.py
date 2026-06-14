from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import ArticleStatus, PostMetrics, Product
from app.modules.statistics.domain.errors import ArticleNotFoundError
from app.modules.statistics.domain.repo import StatisticsRepo


@dataclass(frozen=True)
class ArticleDetailEntry:
    id: str
    name: str
    product: Product
    status: ArticleStatus
    on_air_date: date
    created_at: datetime
    link: Optional[str]
    link_submitted_at: Optional[datetime]
    extraction_status: Optional[str]
    has_content: bool
    metrics: Optional[PostMetrics]
    creator_email: Optional[str]
    claimed_by_email: Optional[str]
    reviewer_email: Optional[str]
    review_round: int
    anchored_feedback_count: int
    general_feedback_count: int


@dataclass(frozen=True)
class GetArticleDetailUseCase(LoggerMixin):
    repo: StatisticsRepo

    async def execute(self, *, article_id: str) -> ArticleDetailEntry:
        found = await self.repo.get_article_with_owner(article_id)
        if found is None:
            raise ArticleNotFoundError()
        article, owner_id = found

        ids: set[str] = {owner_id}
        if article.claimed_by:
            ids.add(article.claimed_by)
        if article.reviewer_user_id:
            ids.add(article.reviewer_user_id)
        emails = await self.repo.email_map(ids)

        anchored, general = await self.repo.feedback_counts(article_id)

        return ArticleDetailEntry(
            id=article.id,
            name=article.name,
            product=article.product,
            status=article.status,
            on_air_date=article.on_air_date,
            created_at=article.created_at,
            link=article.link,
            link_submitted_at=article.link_submitted_at,
            extraction_status=(
                article.extraction_status.value if article.extraction_status else None
            ),
            has_content=bool(article.content and article.content.strip()),
            metrics=article.metrics,
            creator_email=emails.get(owner_id),
            claimed_by_email=emails.get(article.claimed_by) if article.claimed_by else None,
            reviewer_email=emails.get(article.reviewer_user_id) if article.reviewer_user_id else None,
            review_round=article.review_round,
            anchored_feedback_count=anchored,
            general_feedback_count=general,
        )
