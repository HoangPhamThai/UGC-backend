import pytest

from app.modules.workspaces.data.model import (
    AnchorTargetType,
    ArticleStatus,
    Feedback,
    FeedbackAnchor,
    FeedbackStatus,
)
from app.modules.workspaces.domain.errors import FeedbackStateConflictError
from app.modules.workspaces.domain.usecases.delete_feedback import DeleteFeedbackUseCase
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


async def test_delete_draft(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by="u_qc")
    fb = _draft_fb()
    frepo = FakeFeedbackRepo([fb])
    uc = DeleteFeedbackUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=frepo,
    )
    await uc.execute(
        workspace_id="ws_1",
        article_id="art_1",
        feedback_id="fb_d",
        caller=qc,
    )
    assert "fb_d" not in frepo.items


async def test_cannot_delete_open(qc):
    art = make_article(status=ArticleStatus.EDITED, claimed_by="u_qc")
    fb = _draft_fb()
    fb.status = FeedbackStatus.OPEN
    frepo = FakeFeedbackRepo([fb])
    uc = DeleteFeedbackUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=frepo,
    )
    with pytest.raises(FeedbackStateConflictError):
        await uc.execute(
            workspace_id="ws_1",
            article_id="art_1",
            feedback_id="fb_d",
            caller=qc,
        )
