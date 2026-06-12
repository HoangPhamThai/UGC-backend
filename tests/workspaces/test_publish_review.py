import pytest

from app.modules.workspaces.data.model import (
    AnchorTargetType,
    ArticleEventType,
    ArticleStatus,
    Feedback,
    FeedbackAnchor,
    FeedbackStatus,
)
from app.modules.workspaces.domain.errors import ClaimConflictError, ArticleStateConflictError
from app.modules.workspaces.domain.usecases.publish_review import PublishReviewUseCase
from tests.conftest import FakeArticleEventRepo, FakeArticleRepo, FakeFeedbackRepo, make_article


def _fb(fid, status):
    return Feedback(
        id=fid, article_id="art_1", author_id="u_qc", body="x", status=status,
        anchor=FeedbackAnchor(target_type=AnchorTargetType.TEXT, quote="hello"),
    )


async def test_publish_flips_to_feedback_provided_and_opens_drafts(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by="u_qc")
    frepo = FakeFeedbackRepo([_fb("fb_1", FeedbackStatus.DRAFT), _fb("fb_2", FeedbackStatus.DRAFT)])
    arepo = FakeArticleRepo([art])
    events = FakeArticleEventRepo()
    uc = PublishReviewUseCase(article_repo=arepo, feedback_repo=frepo, event_repo=events)

    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)

    assert result.status == ArticleStatus.FEEDBACK_PROVIDED
    assert result.review_round == 1
    assert frepo.items["fb_1"].status == FeedbackStatus.OPEN
    assert frepo.items["fb_2"].status == FeedbackStatus.OPEN
    assert events.events[-1].type == ArticleEventType.REVIEW_PUBLISHED


async def test_publish_with_no_open_after_open_drafts_is_conflict(qc):
    # No drafts and no existing open feedback -> nothing to send back.
    art = make_article(status=ArticleStatus.EDITED, claimed_by="u_qc")
    frepo = FakeFeedbackRepo([_fb("fb_1", FeedbackStatus.RESOLVED)])
    uc = PublishReviewUseCase(
        article_repo=FakeArticleRepo([art]), feedback_repo=frepo, event_repo=FakeArticleEventRepo()
    )
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)


async def test_publish_requires_claim(qc):
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by=None)
    frepo = FakeFeedbackRepo([_fb("fb_1", FeedbackStatus.DRAFT)])
    uc = PublishReviewUseCase(
        article_repo=FakeArticleRepo([art]), feedback_repo=frepo, event_repo=FakeArticleEventRepo()
    )
    with pytest.raises(ClaimConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)


async def test_publish_from_non_review_state_raises(qc):
    art = make_article(status=ArticleStatus.APPROVED, claimed_by="u_qc")
    frepo = FakeFeedbackRepo([_fb("fb_1", FeedbackStatus.DRAFT)])
    uc = PublishReviewUseCase(
        article_repo=FakeArticleRepo([art]), feedback_repo=frepo, event_repo=FakeArticleEventRepo()
    )
    with pytest.raises(ArticleStateConflictError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)


async def test_publish_sets_reviewed_content_snapshot(qc):
    html = "<p>version at publish</p>"
    art = make_article(status=ArticleStatus.SUBMITTED, claimed_by="u_qc")
    art.content = html
    frepo = FakeFeedbackRepo([_fb("fb_1", FeedbackStatus.DRAFT)])
    uc = PublishReviewUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=frepo,
        event_repo=FakeArticleEventRepo(),
    )
    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)
    assert result.reviewed_content == html
    assert result.status == ArticleStatus.FEEDBACK_PROVIDED


async def test_second_publish_overwrites_snapshot(qc):
    art = make_article(status=ArticleStatus.EDITED, claimed_by="u_qc")
    art.content = "<p>round 2 content</p>"
    art.reviewed_content = "<p>old snapshot</p>"
    frepo = FakeFeedbackRepo([_fb("fb_1", FeedbackStatus.DRAFT)])
    uc = PublishReviewUseCase(
        article_repo=FakeArticleRepo([art]),
        feedback_repo=frepo,
        event_repo=FakeArticleEventRepo(),
    )
    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)
    assert result.reviewed_content == "<p>round 2 content</p>"
