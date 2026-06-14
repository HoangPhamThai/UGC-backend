import pytest

from app.modules.workspaces.data.model import ArticleStatus, PostMetrics
from app.modules.workspaces.domain.errors import ArticleNotFoundError
from app.modules.reports.domain.errors import ReportValidationError
from app.modules.reports.domain.usecases.recheck_link_metrics import (
    RecheckLinkMetricsUseCase,
)
from tests.conftest import FakeArticleRepo, make_article

URL = "https://www.tiktok.com/@x/1"
FRESH = {"platform": "tiktok", "url": URL, "views": 200, "favorites": 20,
         "comments": 3, "shares": 2, "reposts": None, "bookmark": 1,
         "account_name": "@x", "nickname": None, "created_at": None,
         "content": None, "images": [], "comments_preview": []}


class StubExtractor:
    def __init__(self, result=None, error=None):
        self._result, self._error = result, error
    async def extract(self, url):
        if self._error:
            raise self._error
        return self._result


def _article(link=URL, metrics=None):
    a = make_article(status=ArticleStatus.APPROVED, aid="art_1")
    a.link = link
    a.metrics = metrics
    return a


@pytest.mark.asyncio
async def test_recheck_returns_stored_fresh_and_diff():
    art = _article(metrics=PostMetrics(platform="tiktok", views=100, favorites=20))
    uc = RecheckLinkMetricsUseCase(
        article_repo=FakeArticleRepo([art]), extractor=StubExtractor(result=FRESH)
    )
    out = await uc.execute(article_id="art_1")
    assert out.fresh.views == 200
    assert out.stored.views == 100
    assert "views" in out.diff and "favorites" not in out.diff
    assert out.diff["views"] == {"stored": 100, "fresh": 200}


@pytest.mark.asyncio
async def test_recheck_missing_article():
    uc = RecheckLinkMetricsUseCase(
        article_repo=FakeArticleRepo([]), extractor=StubExtractor(result=FRESH)
    )
    with pytest.raises(ArticleNotFoundError):
        await uc.execute(article_id="ghost")


@pytest.mark.asyncio
async def test_recheck_no_link_rejected():
    uc = RecheckLinkMetricsUseCase(
        article_repo=FakeArticleRepo([_article(link=None)]),
        extractor=StubExtractor(result=FRESH),
    )
    with pytest.raises(ReportValidationError):
        await uc.execute(article_id="art_1")
