import pytest

from app.modules.users.data.model import UserRole
from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.workspaces.domain.errors import QcMisconfiguredError
from app.modules.workspaces.domain.usecases.list_review_queue import (
    ListReviewQueueUseCase, ReviewQueueGroup,
)
from tests.conftest import FakeArticleRepo, make_article, make_user


def _articles():
    return [
        make_article(aid="a1", status=ArticleStatus.SUBMITTED, product=Product.CL),
        make_article(aid="a2", status=ArticleStatus.EDITED, product=Product.CL),
        make_article(aid="a3", status=ArticleStatus.FEEDBACK_PROVIDED, product=Product.CL),
        make_article(aid="a4", status=ArticleStatus.APPROVED, product=Product.MMF),
    ]


async def test_needs_review_group_for_qc():
    qc = make_user(role=UserRole.QC, products=[Product.CL], uid="u_qc")
    uc = ListReviewQueueUseCase(article_repo=FakeArticleRepo(_articles()))
    result = await uc.execute(caller=qc, group=ReviewQueueGroup.NEEDS_REVIEW, page=1, limit=10)
    ids = {a.id for a in result.items}
    assert ids == {"a1", "a2"} and result.total == 2


async def test_waiting_creator_group():
    qc = make_user(role=UserRole.QC, products=[Product.CL], uid="u_qc")
    uc = ListReviewQueueUseCase(article_repo=FakeArticleRepo(_articles()))
    result = await uc.execute(caller=qc, group=ReviewQueueGroup.WAITING_CREATOR, page=1, limit=10)
    assert {a.id for a in result.items} == {"a3"}


async def test_qc_only_sees_own_products():
    qc = make_user(role=UserRole.QC, products=[Product.CL], uid="u_qc")
    uc = ListReviewQueueUseCase(article_repo=FakeArticleRepo(_articles()))
    result = await uc.execute(caller=qc, group=ReviewQueueGroup.DONE, page=1, limit=10)
    # a4 is APPROVED but product MMF (not in QC's products) -> excluded
    assert result.items == [] and result.total == 0


async def test_superuser_sees_all_products():
    su = make_user(role=UserRole.SUPERUSER, uid="u_su")
    uc = ListReviewQueueUseCase(article_repo=FakeArticleRepo(_articles()))
    result = await uc.execute(caller=su, group=ReviewQueueGroup.DONE, page=1, limit=10)
    assert {a.id for a in result.items} == {"a4"}


async def test_qc_without_products_raises():
    bad = make_user(role=UserRole.QC, products=[Product.CL], uid="u_x")
    object.__setattr__(bad, "qc_products", [])  # simulate misconfigured QC
    uc = ListReviewQueueUseCase(article_repo=FakeArticleRepo(_articles()))
    with pytest.raises(QcMisconfiguredError):
        await uc.execute(caller=bad, group=ReviewQueueGroup.NEEDS_REVIEW, page=1, limit=10)


async def test_pagination_returns_second_page():
    qc = make_user(role=UserRole.QC, products=[Product.CL], uid="u_qc")
    # two needs_review articles, both product CL
    arts = [
        make_article(aid="p1", status=ArticleStatus.SUBMITTED, product=Product.CL),
        make_article(aid="p2", status=ArticleStatus.EDITED, product=Product.CL),
    ]
    uc = ListReviewQueueUseCase(article_repo=FakeArticleRepo(arts))
    page1 = await uc.execute(caller=qc, group=ReviewQueueGroup.NEEDS_REVIEW, page=1, limit=1)
    page2 = await uc.execute(caller=qc, group=ReviewQueueGroup.NEEDS_REVIEW, page=2, limit=1)
    assert len(page1.items) == 1 and len(page2.items) == 1
    assert page1.items[0].id != page2.items[0].id
    assert page1.total == 2 and page2.total == 2
