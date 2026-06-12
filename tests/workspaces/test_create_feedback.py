import pytest

from app.modules.workspaces.data.model import (
    AnchorTargetType,
    ArticleStatus,
    FeedbackAnchor,
    FeedbackStatus,
)
from app.modules.workspaces.domain.errors import ClaimConflictError, ArticleStateConflictError
from app.modules.workspaces.domain.usecases.create_feedback import CreateFeedbackUseCase
from tests.conftest import FakeArticleRepo, FakeFeedbackRepo, make_article


def _text_anchor():
    return FeedbackAnchor(
        target_type=AnchorTargetType.TEXT, quote="hello", prefix="", suffix=" world",
        start_offset=0, end_offset=5,
    )


async def test_create_feedback_saves_draft(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by="u_qc")
    frepo = FakeFeedbackRepo()
    uc = CreateFeedbackUseCase(article_repo=FakeArticleRepo([art]), feedback_repo=frepo)

    fb = await uc.execute(
        workspace_id="ws_1", article_id="art_1", caller=qc,
        body="fix this", anchor=_text_anchor(),
    )

    assert fb.status == FeedbackStatus.DRAFT
    assert fb.author_id == qc.id
    assert fb.anchor.quote == "hello"
    assert frepo.items[fb.id].status == FeedbackStatus.DRAFT


async def test_create_feedback_without_claim_raises(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by=None)
    uc = CreateFeedbackUseCase(
        article_repo=FakeArticleRepo([art]), feedback_repo=FakeFeedbackRepo()
    )
    with pytest.raises(ClaimConflictError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", caller=qc,
            body="x", anchor=_text_anchor(),
        )


async def test_create_feedback_on_non_review_state_raises(qc):
    art = make_article(status=ArticleStatus.APPROVED, claimed_by="u_qc")
    uc = CreateFeedbackUseCase(
        article_repo=FakeArticleRepo([art]), feedback_repo=FakeFeedbackRepo()
    )
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(
            workspace_id="ws_1", article_id="art_1", caller=qc,
            body="x", anchor=_text_anchor(),
        )
