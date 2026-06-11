import pytest

from app.modules.workspaces.data.model import (
    AnchorTargetType,
    ArticleEventType,
    ArticleStatus,
    Feedback,
    FeedbackAnchor,
    FeedbackStatus,
)
from app.modules.workspaces.domain.errors import (
    ClaimConflictError,
    FeedbackNotFoundError,
    FeedbackStateConflictError,
)
from app.modules.workspaces.domain.usecases.set_feedback_status import SetFeedbackStatusUseCase
from tests.conftest import FakeArticleEventRepo, FakeArticleRepo, FakeFeedbackRepo, make_article


def _fb(status):
    return Feedback(
        id="fb_1", article_id="art_1", author_id="u_qc", body="x", status=status,
        anchor=FeedbackAnchor(target_type=AnchorTargetType.TEXT, quote="hello"),
    )


def _ctx(fb_status, claimed_by="u_qc"):
    art = make_article(status=ArticleStatus.EDITED, claimed_by=claimed_by)
    return (
        FakeArticleRepo([art]),
        FakeFeedbackRepo([_fb(fb_status)]),
        FakeArticleEventRepo(),
    )


async def test_resolve_open_feedback(qc):
    arepo, frepo, events = _ctx(FeedbackStatus.OPEN)
    uc = SetFeedbackStatusUseCase(article_repo=arepo, feedback_repo=frepo, event_repo=events)

    fb = await uc.execute(
        workspace_id="ws_1", article_id="art_1", feedback_id="fb_1",
        target=FeedbackStatus.RESOLVED, caller=qc,
    )
    assert fb.status == FeedbackStatus.RESOLVED
    assert fb.resolved_by == qc.id and fb.resolved_at is not None
    assert events.events[-1].type == ArticleEventType.FEEDBACK_RESOLVED


async def test_reopen_resolved_clears_resolution(qc):
    arepo, frepo, events = _ctx(FeedbackStatus.RESOLVED)
    uc = SetFeedbackStatusUseCase(article_repo=arepo, feedback_repo=frepo, event_repo=events)

    fb = await uc.execute(
        workspace_id="ws_1", article_id="art_1", feedback_id="fb_1",
        target=FeedbackStatus.OPEN, caller=qc,
    )
    assert fb.status == FeedbackStatus.OPEN
    assert fb.resolved_by is None and fb.resolved_at is None
    assert events.events[-1].type == ArticleEventType.FEEDBACK_REOPENED


async def test_cannot_resolve_a_draft(qc):
    arepo, frepo, events = _ctx(FeedbackStatus.DRAFT)
    uc = SetFeedbackStatusUseCase(article_repo=arepo, feedback_repo=frepo, event_repo=events)
    with pytest.raises(FeedbackStateConflictError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", feedback_id="fb_1",
            target=FeedbackStatus.RESOLVED, caller=qc,
        )


async def test_requires_claim(qc):
    arepo, frepo, events = _ctx(FeedbackStatus.OPEN, claimed_by=None)
    uc = SetFeedbackStatusUseCase(article_repo=arepo, feedback_repo=frepo, event_repo=events)
    with pytest.raises(ClaimConflictError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", feedback_id="fb_1",
            target=FeedbackStatus.RESOLVED, caller=qc,
        )


async def test_missing_feedback_is_404(qc):
    art = make_article(status=ArticleStatus.EDITED, claimed_by="u_qc")
    uc = SetFeedbackStatusUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(FeedbackNotFoundError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", feedback_id="nope",
            target=FeedbackStatus.RESOLVED, caller=qc,
        )
