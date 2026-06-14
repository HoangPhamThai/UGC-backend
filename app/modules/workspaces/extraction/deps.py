# app/modules/workspaces/extraction/deps.py
from app.modules.workspaces.data.repo import ArticleDataRepository
from app.modules.workspaces.extraction.port import Extractor
from app.modules.workspaces.extraction.runner import run_extraction
from app.modules.workspaces.extraction.unconfigured import UnconfiguredExtractor


def get_extractor() -> Extractor:
    """Return the real PostAnalyzer-backed extractor if available, else a
    fallback that fails cleanly (so the article is marked failed, not crashed)."""
    try:
        from app.modules.workspaces.extraction.post_analyzer_extractor import (
            PostAnalyzerExtractor,
        )
        return PostAnalyzerExtractor()
    except ImportError:
        return UnconfiguredExtractor()


async def run_extraction_task(article_id: str, url: str) -> None:
    """Entry point for FastAPI BackgroundTasks. Builds its own repo (request
    scope is gone by the time this runs) and the configured extractor."""
    await run_extraction(
        article_id,
        url,
        extractor=get_extractor(),
        article_repo=ArticleDataRepository(),
    )
