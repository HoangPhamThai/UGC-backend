import pytest

from app.modules.workspaces.data.model import (
    AnchorTargetType,
    ArticleStatus,
    Feedback,
    FeedbackAnchor,
    FeedbackStatus,
)
from app.modules.workspaces.domain.errors import FeedbackStateConflictError
from app.modules.workspaces.domain.usecases.update_feedback import UpdateFeedbackUseCase
from tests.conftest import FakeArticleRepo, FakeFeedbackRepo, make_article


def _draft_fb():
    return Feedback(
        id="fb_d",
        article_id="art_1",
        author_id="u_qc",
        body="old",
        status=FeedbackStatus.DRAFT,
        anchor=FeedbackAnchor(target_type=AnchorTargetType.TEXT, quote="hi"),
    )


async def test_update_draft_body(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by="u_qc")
    fb = _draft_fb()
    uc = UpdateFeedbackUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([fb]),
    )
    result = await uc.execute(
        workspace_id="ws_1",
        article_id="art_1",
        feedback_id="fb_d",
        body="updated text",
        caller=qc,
    )
    assert result.body == "updated text"


async def test_cannot_update_open_feedback(qc):
    art = make_article(status=ArticleStatus.EDITED, claimed_by="u_qc")
    fb = _draft_fb()
    fb.status = FeedbackStatus.OPEN
    uc = UpdateFeedbackUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo([fb]),
    )
    with pytest.raises(FeedbackStateConflictError):
        await uc.execute(
            workspace_id="ws_1",
            article_id="art_1",
            feedback_id="fb_d",
            body="x",
            caller=qc,
        )
