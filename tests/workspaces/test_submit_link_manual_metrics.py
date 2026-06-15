"""Tests: submit article link WITH manually-entered metrics (no scraping path)."""
import pytest

from app.modules.workspaces.data.model import (
    ArticleStatus,
    ExtractionStatus,
    PostMetrics,
    Workspace,
)
from app.modules.workspaces.domain.usecases.submit_article_link import (
    SubmitArticleLinkUseCase,
)
from tests.conftest import FakeArticleRepo, FakeWorkspaceRepo, creator, make_article

TIKTOK = "https://www.tiktok.com/@x/video/123"


def _setup(*, link=None, edit_count=0, report_id=None):
    art = make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")
    art.link = link
    art.link_edit_count = edit_count
    art.report_id = report_id
    ws = Workspace(id="ws_1", name="W", owner_user_id="u_creator")
    uc = SubmitArticleLinkUseCase(
        workspace_repo=FakeWorkspaceRepo([ws]),
        article_repo=FakeArticleRepo([art]),
    )
    return uc


@pytest.mark.asyncio
async def test_submit_link_with_manual_metrics_saves_directly_extracted(creator):
    uc = _setup(link=None, edit_count=0)
    article = await uc.execute(
        workspace_id="ws_1",
        article_id="art_1",
        caller=creator,
        link=TIKTOK,
        metrics=PostMetrics(views=1000, favorites=50, comments=10, shares=5),
    )
    assert article.extraction_status == ExtractionStatus.EXTRACTED
    assert article.link == TIKTOK
    assert article.metrics is not None
    assert article.metrics.views == 1000
    assert article.metrics.favorites == 50
    assert article.metrics.comments == 10
    assert article.metrics.shares == 5
    assert article.extracted_at is not None


@pytest.mark.asyncio
async def test_submit_link_with_partial_manual_metrics(creator):
    """Only some metrics provided — others remain None."""
    uc = _setup(link=None, edit_count=0)
    article = await uc.execute(
        workspace_id="ws_1",
        article_id="art_1",
        caller=creator,
        link=TIKTOK,
        metrics=PostMetrics(views=999),
    )
    assert article.extraction_status == ExtractionStatus.EXTRACTED
    assert article.metrics.views == 999
    assert article.metrics.favorites is None
    assert article.metrics.comments is None
    assert article.metrics.shares is None


@pytest.mark.asyncio
async def test_submit_link_without_metrics_uses_pending_path(creator):
    """No metrics provided → existing behavior: PENDING, no metrics stored."""
    uc = _setup(link=None, edit_count=0)
    article = await uc.execute(
        workspace_id="ws_1",
        article_id="art_1",
        caller=creator,
        link=TIKTOK,
        metrics=None,
    )
    assert article.extraction_status == ExtractionStatus.PENDING
    assert article.link == TIKTOK
    assert article.metrics is None
