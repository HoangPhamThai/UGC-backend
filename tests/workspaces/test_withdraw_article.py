import pytest

from app.modules.workspaces.data.model import ArticleEventType, ArticleStatus, Workspace
from app.modules.workspaces.domain.errors import (
    ArticleStateConflictError,
    ClaimConflictError,
    WorkspaceNotFoundError,
)
from app.modules.workspaces.domain.usecases.withdraw_article import WithdrawArticleUseCase
from tests.conftest import (
    FakeArticleEventRepo,
    FakeArticleRepo,
    FakeWorkspaceRepo,
    make_article,
)


def _ws():
    return Workspace(id="ws_1", name="W", owner_user_id="u_creator")


async def test_withdraw_unclaimed_submitted_returns_to_not_submitted(creator):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by=None)
    arepo = FakeArticleRepo([art])
    events = FakeArticleEventRepo()
    uc = WithdrawArticleUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]), article_repo=arepo, event_repo=events
    )

    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)

    assert result.status == ArticleStatus.NOT_SUBMITTED
    assert events.events[-1].type == ArticleEventType.WITHDRAWN


async def test_withdraw_when_claimed_raises_conflict(creator):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by="u_qc")
    uc = WithdrawArticleUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(ClaimConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)


async def test_withdraw_from_non_submitted_raises_state_conflict(creator):
    art = make_article(status=ArticleStatus.EDITED, claimed_by=None)
    uc = WithdrawArticleUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)


async def test_withdraw_not_owner_is_404(creator):
    ws = Workspace(id="ws_1", name="W", owner_user_id="someone_else")
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by=None)
    uc = WithdrawArticleUseCase(
        workspace_repo=FakeWorkspaceRepo([ws]),
        article_repo=FakeArticleRepo([art]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(WorkspaceNotFoundError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)
