from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.usecases.get_summary import GetSummaryUseCase
from tests.conftest import FakeStatisticsRepo, make_article_stat


def _repo():
    stats = [
        make_article_stat(aid="draft", status=ArticleStatus.NOT_SUBMITTED),
        make_article_stat(aid="await1", status=ArticleStatus.SUBMITTED, claimed_by=None),
        make_article_stat(aid="await2", status=ArticleStatus.EDITED, claimed_by=None),
        # claimed but undecided -> in_review (not awaiting)
        make_article_stat(aid="claimed", status=ArticleStatus.SUBMITTED, claimed_by="u_qc"),
        # feedback returned, QC still handling -> in_review
        make_article_stat(aid="fb", status=ArticleStatus.FEEDBACK_PROVIDED, claimed_by="u_qc"),
        make_article_stat(aid="rej", status=ArticleStatus.REJECTED, rejected_by="u_qc"),
        make_article_stat(aid="appr_qc", status=ArticleStatus.APPROVED, reviewer_user_id="u_qc"),
        make_article_stat(aid="appr_auto", status=ArticleStatus.APPROVED),
    ]
    return FakeStatisticsRepo(stats=stats, auto_ids={"appr_auto"})


async def test_summary_counts():
    uc = GetSummaryUseCase(repo=_repo())
    res = await uc.execute(from_dt=None, to_dt=None, product=None)
    assert res.total == 7  # all 8 minus the not_submitted draft
    assert res.awaiting_review == 2  # await1, await2
    assert res.in_review == 2  # claimed, fb
    assert res.rejected == 1
    assert res.approved == 1  # appr_qc only
    assert res.auto_approved == 1  # appr_auto only


async def test_summary_empty_window_is_all_zeros():
    uc = GetSummaryUseCase(repo=FakeStatisticsRepo(stats=[], auto_ids=set()))
    res = await uc.execute(from_dt=None, to_dt=None, product=None)
    assert (res.total, res.awaiting_review, res.in_review, res.approved, res.rejected, res.auto_approved) == (0, 0, 0, 0, 0, 0)


async def test_summary_product_filter_is_passed_through():
    stats = [
        make_article_stat(aid="cl", status=ArticleStatus.SUBMITTED, product=Product.CL),
        make_article_stat(aid="fd", status=ArticleStatus.SUBMITTED, product=Product.FD),
    ]
    uc = GetSummaryUseCase(repo=FakeStatisticsRepo(stats=stats, auto_ids=set()))
    res = await uc.execute(from_dt=None, to_dt=None, product=Product.CL)
    assert res.total == 1
