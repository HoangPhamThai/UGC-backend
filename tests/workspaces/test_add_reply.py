import pytest

from app.modules.workspaces.data.model import (
    AnchorTargetType,
    ArticleEventType,
    ArticleStatus,
    Feedback,
    FeedbackAnchor,
    FeedbackStatus,
    Workspace,
)
from app.modules.workspaces.domain.errors import ClaimConflictError, FeedbackNotFoundError, ArticleNotFoundError
from app.modules.workspaces.domain.usecases.add_reply import AddReplyUseCase
from tests.conftest import (
    FakeArticleEventRepo,
    FakeArticleRepo,
    FakeFeedbackRepo,
    FakeWorkspaceRepo,
    make_article,
)


def _fb():
    return Feedback(
        id="fb_1", article_id="art_1", author_id="u_qc", body="x",
        status=FeedbackStatus.OPEN,
        anchor=FeedbackAnchor(target_type=AnchorTargetType.TEXT, quote="hello"),
    )


def _ws():
    return Workspace(id="ws_1", name="W", owner_user_id="u_creator")


async def test_qc_reply_appends_and_keeps_status(qc):
    art = make_article(status=ArticleStatus.FEEDBACK_PROVIDED, claimed_by="u_qc")
    frepo = FakeFeedbackRepo([_fb()])
    events = FakeArticleEventRepo()
    uc = AddReplyUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        feedback_repo=frepo,
        event_repo=events,
    )

    fb = await uc.execute(
        workspace_id="ws_1", article_id="art_1", feedback_id="fb_1",
        body="thanks", caller=qc,
    )

    assert len(fb.replies) == 1
    assert fb.replies[0].author_id == qc.id
    assert art.status == ArticleStatus.FEEDBACK_PROVIDED  # unchanged
    assert events.events[-1].type == ArticleEventType.REPLY_ADDED


async def test_creator_owner_can_reply(creator):
    art = make_article(status=ArticleStatus.FEEDBACK_PROVIDED, claimed_by="u_qc")
    uc = AddReplyUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([_fb()]),
        event_repo=FakeArticleEventRepo(),
    )
    fb = await uc.execute(
        workspace_id="ws_1", article_id="art_1", feedback_id="fb_1",
        body="done", caller=creator,
    )
    assert fb.replies[0].author_id == creator.id


async def test_reply_to_missing_feedback_is_404(qc):
    art = make_article(status=ArticleStatus.FEEDBACK_PROVIDED, claimed_by="u_qc")
    uc = AddReplyUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(FeedbackNotFoundError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", feedback_id="nope",
            body="x", caller=qc,
        )


async def test_non_claiming_qc_cannot_reply(qc):
    art = make_article(status=ArticleStatus.FEEDBACK_PROVIDED, claimed_by="u_other_qc")
    uc = AddReplyUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([_fb()]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(ClaimConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1",
                         feedback_id="fb_1", body="x", caller=qc)


async def test_non_owner_creator_cannot_reply():
    from app.modules.users.data.model import UserRole
    from tests.conftest import make_user
    art = make_article(status=ArticleStatus.FEEDBACK_PROVIDED, claimed_by="u_qc")
    intruder = make_user(role=UserRole.CREATOR, uid="u_intruder")
    uc = AddReplyUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([_fb()]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(ArticleNotFoundError):
        await uc.execute(workspace_id="ws_1", article_id="art_1",
                         feedback_id="fb_1", body="x", caller=intruder)
