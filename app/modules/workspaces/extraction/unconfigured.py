# app/modules/workspaces/extraction/unconfigured.py
class UnconfiguredExtractor:
    """Fallback used when no real extractor is wired. Always fails, so the
    article lands in extraction_status=failed with a clear message."""

    async def extract(self, url: str) -> dict:
        raise RuntimeError("No metrics extractor is configured")
