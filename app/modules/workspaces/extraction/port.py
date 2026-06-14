# app/modules/workspaces/extraction/port.py
from typing import Protocol


class Extractor(Protocol):
    async def extract(self, url: str) -> dict:
        """Return the post_analyzer unified-schema dict for the URL, or raise."""
        ...
