import pytest

from app.modules.workspaces.data.model import ArticleStatus, ExtractionStatus
from app.modules.workspaces.extraction.runner import run_extraction
from tests.conftest import FakeArticleRepo, make_article

URL = "https://www.tiktok.com/@x/photo/1"

UNIFIED = {
    "platform": "tiktok", "url": URL, "account_name": "@x", "nickname": None,
    "created_at": None, "content": "hi", "views": 100, "favorites": 10,
    "comments": 2, "shares": 1, "reposts": None, "bookmark": 5,
    "images": [], "comments_preview": [],
}


class StubExtractor:
    def __init__(self, *, result=None, error=None):
        self._result = result
        self._error = error

    async def extract(self, url: str) -> dict:
        if self._error:
            raise self._error
        return self._result


def _article_with_link(url=URL):
    a = make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")
    a.link = url
    a.extraction_status = ExtractionStatus.PENDING
    return a


@pytest.mark.asyncio
async def test_success_stores_metrics_and_marks_extracted():
    repo = FakeArticleRepo([_article_with_link()])
    await run_extraction(
        "art_1", URL, extractor=StubExtractor(result=UNIFIED), article_repo=repo
    )
    a = repo.items["art_1"]
    assert a.extraction_status == ExtractionStatus.EXTRACTED
    assert a.metrics.views == 100


@pytest.mark.asyncio
async def test_failure_marks_failed_and_increments_attempts():
    repo = FakeArticleRepo([_article_with_link()])
    await run_extraction(
        "art_1", URL,
        extractor=StubExtractor(error=RuntimeError("boom")),
        article_repo=repo,
    )
    a = repo.items["art_1"]
    assert a.extraction_status == ExtractionStatus.FAILED
    assert a.extraction_error == "boom"
    assert a.extraction_attempts == 1


@pytest.mark.asyncio
async def test_stale_extraction_is_ignored_when_link_changed():
    repo = FakeArticleRepo([_article_with_link("https://www.tiktok.com/@x/photo/NEW")])
    await run_extraction(
        "art_1", URL, extractor=StubExtractor(result=UNIFIED), article_repo=repo
    )
    a = repo.items["art_1"]
    assert a.extraction_status == ExtractionStatus.PENDING
    assert a.metrics is None
