# app/modules/workspaces/extraction/runner.py
import asyncio
import logging

from app.modules.workspaces.data.model import PostMetrics
from app.modules.workspaces.domain.repo import ArticleRepo
from app.modules.workspaces.extraction.port import Extractor

logger = logging.getLogger("workspaces.extraction")

EXTRACTION_TIMEOUT_S = 90


async def run_extraction(
    article_id: str,
    url: str,
    *,
    extractor: Extractor,
    article_repo: ArticleRepo,
    timeout_s: int = EXTRACTION_TIMEOUT_S,
) -> None:
    """Scrape `url` and persist the outcome. Result writes are url-filtered, so
    if the article's link changed while we ran, this no-ops. Never raises."""
    try:
        data = await asyncio.wait_for(extractor.extract(url), timeout=timeout_s)
        metrics = PostMetrics.model_validate(data)
        await article_repo.record_extraction_success(
            article_id, url=url, metrics=metrics
        )
        logger.info("Extraction ok: article=%s", article_id)
    except Exception as e:  # noqa: BLE001 — record every failure, never propagate
        await article_repo.record_extraction_failure(
            article_id, url=url, error=str(e)[:500]
        )
        logger.warning("Extraction failed: article=%s err=%s", article_id, e)
