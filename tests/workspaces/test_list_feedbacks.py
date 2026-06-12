import pytest

from app.modules.users.data.model import UserRole
from app.modules.workspaces.data.model import (
    AnchorTargetType, ArticleStatus, Feedback, FeedbackAnchor, FeedbackStatus, Product, Workspace,
)
from app.modules.workspaces.domain.errors import ArticleNotFoundError
from app.modules.workspaces.domain.usecases.list_feedbacks import ListFeedbacksUseCase
from tests.conftest import FakeArticleRepo, FakeFeedbackRepo, FakeWorkspaceRepo, make_article, make_user


def _fb(fid, status, author="u_qc"):
    return Feedback(
        id=fid, article_id="art_1", author_id=author, body="x", status=status,
        anchor=FeedbackAnchor(target_type=AnchorTargetType.TEXT, quote="hello"),
    )


def _ws():
    return Workspace(id="ws_1", name="W", owner_user_id="u_creator")


def _ctx(feedbacks):
    art = make_article(status=ArticleStatus.EDITED, claimed_by="u_qc", product=Product.CL)
    return ListFeedbacksUseCase(
        workspace_repo=FakeWorkspaceRepo([_ws()]),
        article_repo=FakeArticleRepo([art]),
        feedback_repo=FakeFeedbackRepo(feedbacks),
    )


async def test_qc_author_sees_their_drafts():
    qc = make_user(role=UserRole.QC, products=[Product.CL], uid="u_qc")
    uc = _ctx([_fb("f1", FeedbackStatus.OPEN), _fb("f2", FeedbackStatus.DRAFT, author="u_qc")])
    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=qc)
    assert {f.id for f in result} == {"f1", "f2"}


async def test_creator_does_not_see_drafts():
    creator = make_user(role=UserRole.CREATOR, uid="u_creator")
    uc = _ctx([_fb("f1", FeedbackStatus.OPEN), _fb("f2", FeedbackStatus.DRAFT, author="u_qc")])
    result = await uc.execute(workspace_id="ws_1", article_id="art_1", caller=creator)
    assert {f.id for f in result} == {"f1"}


async def test_non_owner_creator_is_404():
    intruder = make_user(role=UserRole.CREATOR, uid="u_intruder")
    uc = _ctx([_fb("f1", FeedbackStatus.OPEN)])
    with pytest.raises(ArticleNotFoundError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=intruder)


async def test_out_of_scope_qc_is_404():
    other_qc = make_user(role=UserRole.QC, products=[Product.MMF], uid="u_other")
    uc = _ctx([_fb("f1", FeedbackStatus.OPEN)])
    with pytest.raises(ArticleNotFoundError):
        await uc.execute(workspace_id="ws_1", article_id="art_1", caller=other_qc)
