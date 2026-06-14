import pytest

from app.modules.workspaces.data.model import ArticleStatus, ExtractionStatus, Workspace
from app.modules.workspaces.domain.errors import (
    ArticleStateConflictError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.usecases.retry_extraction import (
    RetryExtractionUseCase,
)
from tests.conftest import FakeArticleRepo, FakeWorkspaceRepo, creator, make_article

URL = "https://www.tiktok.com/@x/photo/1"


def _setup(*, link=URL, report_id=None, status=ExtractionStatus.FAILED):
    art = make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")
    art.link = link
    art.report_id = report_id
    art.extraction_status = status
    ws = Workspace(id="ws_1", name="W", owner_user_id="u_creator")
    return RetryExtractionUseCase(
        workspace_repo=FakeWorkspaceRepo([ws]),
        article_repo=FakeArticleRepo([art]),
    )


@pytest.mark.asyncio
async def test_retry_sets_pending(creator):
    uc = _setup()
    out = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)
    assert out.extraction_status == ExtractionStatus.PENDING


@pytest.mark.asyncio
async def test_retry_without_link_is_rejected(creator):
    uc = _setup(link=None)
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)


@pytest.mark.asyncio
async def test_retry_on_reported_article_is_rejected(creator):
    uc = _setup(report_id="rpt_1")
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)


@pytest.mark.asyncio
async def test_retry_wrong_owner_is_rejected(creator):
    art = make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")
    art.link = URL
    ws = Workspace(id="ws_1", name="W", owner_user_id="someone_else")
    uc = RetryExtractionUseCase(
        workspace_repo=FakeWorkspaceRepo([ws]),
        article_repo=FakeArticleRepo([art]),
    )
    with pytest.raises(WorkspaceNotFoundError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)


def test_retry_route_is_registered():
    from app.modules.workspaces.presentation.routes import router
    paths = {r.path for r in router.routes}
    assert "/workspaces/{workspace_id}/articles/{article_id}/link/extract" in paths
