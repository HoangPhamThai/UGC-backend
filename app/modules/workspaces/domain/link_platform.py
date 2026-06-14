# app/modules/workspaces/domain/link_platform.py
"""Standalone platform detection for submitted article links. Mirrors
post_analyzer.PostAnalyzer.detect_platform so Phase 2's vendored scraper and
this Phase 1 validator agree on what counts as a supported URL."""
import re
from typing import Optional


def detect_platform(url: str) -> Optional[str]:
    """Return 'tiktok', 'threads', or None."""
    if re.search(r"https?://([\w.-]+\.)?tiktok\.com/", url, re.I):
        return "tiktok"
    if re.search(r"https?://([\w.-]+\.)?threads\.(com|net)/", url, re.I):
        return "threads"
    return None
