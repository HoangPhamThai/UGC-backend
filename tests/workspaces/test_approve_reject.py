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
    ArticleStateConflictError,
    ClaimConflictError,
    InvalidInputError,
)
from app.modules.workspaces.domain.usecases.approve_article import ApproveArticleUseCase
from app.modules.workspaces.domain.usecases.reject_article import RejectArticleUseCase
from tests.conftest import FakeArticleEventRepo, FakeArticleRepo, FakeFeedbackRepo, make_article


def _open_fb():
    return Feedback(
        id="fb_1", article_id="art_1", author_id="u_qc", body="x",
        status=FeedbackStatus.OPEN,
        anchor=FeedbackAnchor(target_type=AnchorTargetType.TEXT, quote="hello"),
    )


async def test_approve_blocked_by_open_feedback(qc):
    art = make_article(status=ArticleStatus.EDITED, claimed_by="u_qc")
    uc = ApproveArticleUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([_open_fb()]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)


async def test_approve_succeeds_with_no_open_feedback(qc):
    art = make_article(status=ArticleStatus.EDITED, claimed_by="u_qc")
    events = FakeArticleEventRepo()
    uc = ApproveArticleUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([]),
        event_repo=events,
    )
    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)
    assert result.status == ArticleStatus.APPROVED
    assert events.events[-1].type == ArticleEventType.APPROVED


async def test_approve_requires_claim(qc):
    art = make_article(status=ArticleStatus.EDITED, claimed_by=None)
    uc = ApproveArticleUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([]),
        event_repo=FakeArticleEventRepo(),
    )
    with pytest.raises(ClaimConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)


async def test_reject_requires_reason(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by="u_qc")
    uc = RejectArticleUseCase(
        article_repo=FakeArticleRepo([art]), event_repo=FakeArticleEventRepo()
    )
    with pytest.raises(InvalidInputError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc, reason="   ")


async def test_reject_stores_reason_and_logs(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by="u_qc")
    events = FakeArticleEventRepo()
    uc = RejectArticleUseCase(article_repo=FakeArticleRepo([art]), event_repo=events)
    result = await uc.execute(
        workspace_id="ws_1", article_id="art_1", caller=qc, reason="off topic"
    )
    assert result.status == ArticleStatus.REJECTED
    assert result.reject_reason == "off topic"
    assert result.rejected_by == qc.id
    assert events.events[-1].type == ArticleEventType.REJECTED


async def test_reject_requires_claim(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by=None)
    uc = RejectArticleUseCase(article_repo=FakeArticleRepo([art]), event_repo=FakeArticleEventRepo())
    with pytest.raises(ClaimConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc, reason="x")
