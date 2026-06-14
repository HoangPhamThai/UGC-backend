# app/modules/workspaces/extraction/post_analyzer_extractor.py
from app.modules.workspaces.extraction.vendor.post_analyzer import PostAnalyzer


class PostAnalyzerExtractor:
    """Real Extractor: wraps the vendored PostAnalyzer. TikTok uses stdlib HTTP;
    Threads launches headless Chromium via Playwright (must be installed in the
    image — see Dockerfile)."""

    def __init__(self, *, headless: bool = True, n_comments: int = 2) -> None:
        self._analyzer = PostAnalyzer(headless=headless, n_comments=n_comments)

    async def extract(self, url: str) -> dict:
        return await self._analyzer.analyze(url)
