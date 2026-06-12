import pytest

from app.modules.workspaces.data.model import ArticleEventType, ArticleStatus, Workspace
from app.modules.workspaces.domain.usecases.submit_article import SubmitArticleUseCase
from tests.conftest import (
    FakeArticleEventRepo,
    FakeArticleRepo,
    FakeWorkspaceRepo,
    make_article,
)


def _ws():
    return Workspace(id="ws_1", name="W", owner_user_id="u_creator")


async def test_first_submit_emits_submitted_event(creator):
    art = make_article(status=ArticleStatus.NOT_SUBMITTED, claimed_by=None)
    events = FakeArticleEventRepo()
    uc = SubmitArticleUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        event_repo=events,
    )
    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)
    assert result.status == ArticleStatus.SUBMITTED
    assert result.last_activity_by == creator.id
    assert events.events[-1].type == ArticleEventType.SUBMITTED


async def test_resubmit_emits_edited_resubmitted_event(creator):
    art = make_article(status=ArticleStatus.FEEDBACK_PROVIDED, claimed_by="u_qc")
    events = FakeArticleEventRepo()
    uc = SubmitArticleUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        event_repo=events,
    )
    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)
    assert result.status == ArticleStatus.EDITED
    assert result.last_activity_by == creator.id
    assert events.events[-1].type == ArticleEventType.EDITED_RESUBMITTED


async def test_submit_from_non_submittable_status_raises(creator):
    from app.modules.workspaces.domain.errors import ArticleStateConflictError
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by=None)
    uc = SubmitArticleUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)
