import pytest

from app.modules.workspaces.data.model import ArticleStatus, Workspace
from app.modules.workspaces.domain.errors import ArticleNotFoundError, WorkspaceNotFoundError
from app.modules.workspaces.domain.usecases.get_article import GetArticleUseCase
from tests.conftest import FakeArticleRepo, FakeWorkspaceRepo, make_article, make_user
from app.modules.users.data.model import UserRole


def _uc(owner="u_creator"):
    art = make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")
    ws = Workspace(id="ws_1", name="W", owner_user_id=owner)
    return GetArticleUseCase(
        workspace_repo=FakeWorkspaceRepo([ws]), article_repo=FakeArticleRepo([art])
    ), art


@pytest.mark.asyncio
async def test_owner_gets_article():
    uc, art = _uc()
    creator = make_user(role=UserRole.CREATOR, uid="u_creator")
    out = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)
    assert out.id == "art_1"


@pytest.mark.asyncio
async def test_non_owner_creator_rejected():
    uc, _ = _uc(owner="someone_else")
    creator = make_user(role=UserRole.CREATOR, uid="u_creator")
    with pytest.raises(WorkspaceNotFoundError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)


@pytest.mark.asyncio
async def test_missing_article_rejected():
    art = make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")
    ws = Workspace(id="ws_1", name="W", owner_user_id="u_creator")
    uc = GetArticleUseCase(workspace_repo=FakeWorkspaceRepo([ws]), article_repo=FakeArticleRepo([art]))
    creator = make_user(role=UserRole.CREATOR, uid="u_creator")
    with pytest.raises(ArticleNotFoundError):
        await uc.execute(workspace_id="ws_1", article_id="ghost", caller=creator)
