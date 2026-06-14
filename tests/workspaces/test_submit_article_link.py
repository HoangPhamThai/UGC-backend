import pytest

from app.modules.workspaces.data.model import ArticleStatus, Workspace
from app.modules.workspaces.domain.errors import (
    ArticleStateConflictError,
    InvalidInputError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.usecases.submit_article_link import (
    SubmitArticleLinkUseCase,
)
from tests.conftest import FakeArticleRepo, FakeWorkspaceRepo, creator, make_article

TIKTOK = "https://www.tiktok.com/@x/photo/1"
TIKTOK2 = "https://www.tiktok.com/@x/photo/2"


def _setup(*, status=ArticleStatus.APPROVED, link=None, edit_count=0, report_id=None):
    art = make_article(status=status, aid="art_1", workspace_id="ws_1")
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
async def test_first_submit_sets_link_without_consuming_edit(creator):
    uc = _setup(link=None, edit_count=0)
    out = await uc.execute(
        workspace_id="ws_1", article_id="art_1", caller=creator, link=TIKTOK
    )
    assert out.link == TIKTOK
    assert out.link_edit_count == 0
    assert out.link_submitted_at is not None


@pytest.mark.asyncio
async def test_editing_to_new_url_increments_count(creator):
    uc = _setup(link=TIKTOK, edit_count=0)
    out = await uc.execute(
        workspace_id="ws_1", article_id="art_1", caller=creator, link=TIKTOK2
    )
    assert out.link == TIKTOK2
    assert out.link_edit_count == 1


@pytest.mark.asyncio
async def test_resubmitting_same_url_is_noop(creator):
    uc = _setup(link=TIKTOK, edit_count=2)
    out = await uc.execute(
        workspace_id="ws_1", article_id="art_1", caller=creator, link=TIKTOK
    )
    assert out.link_edit_count == 2  # unchanged


@pytest.mark.asyncio
async def test_sixth_change_is_rejected(creator):
    uc = _setup(link=TIKTOK, edit_count=5)
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", caller=creator, link=TIKTOK2
        )


@pytest.mark.asyncio
async def test_non_approved_is_rejected(creator):
    uc = _setup(status=ArticleStatus.SUBMITTED)
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", caller=creator, link=TIKTOK
        )


@pytest.mark.asyncio
async def test_report_locked_is_rejected(creator):
    uc = _setup(link=TIKTOK, report_id="rpt_1")
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", caller=creator, link=TIKTOK2
        )


@pytest.mark.asyncio
async def test_bad_url_is_rejected(creator):
    uc = _setup()
    with pytest.raises(InvalidInputError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", caller=creator,
            link="https://facebook.com/x",
        )


@pytest.mark.asyncio
async def test_wrong_owner_is_rejected(creator):
    art = make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")
    ws = Workspace(id="ws_1", name="W", owner_user_id="someone_else")
    uc = SubmitArticleLinkUseCase(
        workspace_repo=FakeWorkspaceRepo([ws]),
        article_repo=FakeArticleRepo([art]),
    )
    with pytest.raises(WorkspaceNotFoundError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", caller=creator, link=TIKTOK
        )
