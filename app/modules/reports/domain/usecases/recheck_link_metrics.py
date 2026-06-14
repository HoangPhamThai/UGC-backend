# app/modules/reports/domain/usecases/recheck_link_metrics.py
import asyncio
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.reports.domain.errors import ReportValidationError
from app.modules.workspaces.data.model import PostMetrics
from app.modules.workspaces.domain.errors import ArticleNotFoundError
from app.modules.workspaces.domain.repo import ArticleRepo
from app.modules.workspaces.extraction.port import Extractor

_NUMERIC_FIELDS = ("views", "favorites", "comments", "shares", "reposts", "bookmark")
_TIMEOUT_S = 90


@dataclass(frozen=True)
class RecheckResult:
    stored: Optional[PostMetrics]
    fresh: PostMetrics
    diff: dict


@dataclass(frozen=True)
class RecheckLinkMetricsUseCase(LoggerMixin):
    """Re-scrape an article's link and compare to the stored metrics WITHOUT
    persisting anything (spec §8.1, agent verification)."""

    article_repo: ArticleRepo
    extractor: Extractor

    async def execute(self, *, article_id: str) -> RecheckResult:
        article = await self.article_repo.get_by_id(article_id)
        if article is None:
            raise ArticleNotFoundError()
        if not article.link:
            raise ReportValidationError("Article has no link to re-check")

        data = await asyncio.wait_for(
            self.extractor.extract(article.link), timeout=_TIMEOUT_S
        )
        fresh = PostMetrics.model_validate(data)
        stored = article.metrics

        diff: dict = {}
        for f in _NUMERIC_FIELDS:
            s = getattr(stored, f) if stored else None
            n = getattr(fresh, f)
            if s != n:
                diff[f] = {"stored": s, "fresh": n}
        return RecheckResult(stored=stored, fresh=fresh, diff=diff)
