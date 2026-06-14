"""
PostAnalyzer — one entry point for scraping TikTok and Threads posts.

Detects the platform from the URL, dispatches to the right scraper, and
returns a unified dict that is the SAME SHAPE regardless of platform.
Fields that don't apply to a platform are present but set to None / [].

Usage:
    analyzer = PostAnalyzer()

    # async (preferred — Threads is async under the hood):
    data = await analyzer.analyze(url)

    # sync wrapper:
    data = analyzer.analyze_sync(url)

Unified schema:
    platform           "tiktok" | "threads"
    url                the input URL (unmodified)
    account_name       @handle of the poster
    nickname           display name (tiktok only; None for threads)
    created_at         ISO 8601 UTC, e.g. "2026-03-08T01:00:00+00:00"
    content            caption / post text
    views              playCount / view_count
    favorites          likes (heart icon on both platforms)
    comments           reply count
    shares             share count
    reposts            threads-only; None for tiktok
    bookmark           tiktok-only (collectCount, bookmark icon);
                       None for threads
    images             list of media URLs (high-res when available)
    comments_preview   threads-only; [] for tiktok
"""

from __future__ import annotations

import asyncio
import re
from typing import Any


UNIFIED_KEYS = (
    "platform", "url",
    "account_name", "nickname", "created_at", "content",
    "views", "favorites", "comments", "shares",
    "reposts", "bookmark",
    "images", "comments_preview",
)


class PostAnalyzer:
    def __init__(self, *, headless: bool = True, n_comments: int = 2) -> None:
        self.headless = headless
        self.n_comments = n_comments

    # ---- Public API ------------------------------------------------------
    @staticmethod
    def detect_platform(url: str) -> str | None:
        """Return 'tiktok', 'threads', or None."""
        if re.search(r"https?://([\w.-]+\.)?tiktok\.com/", url, re.I):
            return "tiktok"
        if re.search(r"https?://([\w.-]+\.)?threads\.(com|net)/", url, re.I):
            return "threads"
        return None

    async def analyze(self, url: str) -> dict[str, Any]:
        platform = self.detect_platform(url)
        if platform == "tiktok":
            # tiktok scrape is stdlib HTTP but blocking — run off the
            # event loop so an async caller isn't stalled.
            raw = await asyncio.to_thread(self._scrape_tiktok, url)
            return self._unify_tiktok(raw, url)
        if platform == "threads":
            raw = await self._scrape_threads(url)
            return self._unify_threads(raw, url)
        raise ValueError(f"unsupported URL (not tiktok or threads): {url!r}")

    def analyze_sync(self, url: str) -> dict[str, Any]:
        return asyncio.run(self.analyze(url))

    # ---- TikTok ----------------------------------------------------------
    def _scrape_tiktok(self, url: str) -> dict[str, Any]:
        # Lazy import: don't pull Playwright (Threads dep) just to do
        # a TikTok scrape, and vice versa.
        from app.modules.workspaces.extraction.vendor import tiktop_scapper
        return tiktop_scapper.scrape(url)

    @staticmethod
    def _unify_tiktok(raw: dict[str, Any], url: str) -> dict[str, Any]:
        return {
            "platform": "tiktok",
            "url": url,
            "account_name": raw.get("account_name"),
            "nickname": raw.get("nickname"),
            "created_at": raw.get("created_at"),
            "content": raw.get("content"),
            "views": raw.get("views"),
            "favorites": raw.get("favorites"),
            "comments": raw.get("comments"),
            "shares": raw.get("shares"),
            "reposts": None,
            "bookmark": raw.get("bookmark"),
            "images": [],
            "comments_preview": [],
        }

    # ---- Threads ---------------------------------------------------------
    async def _scrape_threads(self, url: str) -> dict[str, Any]:
        from app.modules.workspaces.extraction.vendor import content_scapper_v3
        return await content_scapper_v3.scrape(
            url=url,
            n_comments=self.n_comments,
            headless=self.headless,
            debug=False,
        )

    @staticmethod
    def _unify_threads(raw: dict[str, Any], url: str) -> dict[str, Any]:
        return {
            "platform": "threads",
            "url": url,
            "account_name": raw.get("account_name"),
            "nickname": None,
            "created_at": raw.get("created_at"),
            "content": raw.get("content"),
            "views": raw.get("views"),
            "favorites": raw.get("favorites"),
            "comments": raw.get("comments"),
            "shares": raw.get("shares"),
            "reposts": raw.get("reposts"),
            "bookmark": None,
            "images": list(raw.get("images") or []),
            "comments_preview": list(raw.get("comments_preview") or []),
        }


def main() -> None:
    import json
    import sys

    if len(sys.argv) < 2:
        print("usage: python post_analyzer.py <url>", file=sys.stderr)
        sys.exit(2)
    data = PostAnalyzer().analyze_sync(sys.argv[1])
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

## Test threads: https://www.threads.com/@ha.anhyu/post/DMPn8Swz8re
## Test tiktok: https://www.tiktok.com/@cici.ajoyer/photo/7615241272583916818