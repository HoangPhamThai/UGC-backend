from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.repo import QcRef
from app.modules.statistics.domain.usecases.get_qc_breakdown import (
    GetQcBreakdownUseCase,
)
from tests.conftest import FakeStatisticsRepo, make_article_stat


def _repo():
    qcs = [
        QcRef(id="qc1", email="qc1@x.com", products=[Product.CL]),
        QcRef(id="qc2", email="qc2@x.com", products=[Product.FD, Product.MMF]),
    ]
    stats = [
        # qc1: 1 claimed+approved (QC), 1 claimed+auto-approved, 1 rejected
        make_article_stat(aid="a1", status=ArticleStatus.APPROVED, claimed_by="qc1", reviewer_user_id="qc1"),
        make_article_stat(aid="a2", status=ArticleStatus.APPROVED, claimed_by="qc1", reviewer_user_id="qc1"),
        make_article_stat(aid="a3", status=ArticleStatus.REJECTED, claimed_by="qc1", rejected_by="qc1"),
        # qc2: 1 claimed, not yet decided
        make_article_stat(aid="b1", status=ArticleStatus.SUBMITTED, claimed_by="qc2"),
    ]
    # a2 was auto-approved (e.g. due date passed while qc1 held it)
    return FakeStatisticsRepo(stats=stats, auto_ids={"a2"}, qcs=qcs)


async def test_qc_breakdown_rows():
    uc = GetQcBreakdownUseCase(repo=_repo())
    res = await uc.execute(from_dt=None, to_dt=None, product=None)
    rows = {r.qc_id: r for r in res.items}
    assert set(rows) == {"qc1", "qc2"}

    q1 = rows["qc1"]
    assert q1.email == "qc1@x.com"
    assert q1.products == [Product.CL]
    assert q1.claimed == 3
    assert q1.approved == 1  # a1 (a2 is auto, excluded)
    assert q1.rejected == 1  # a3
    assert q1.auto_approved_after_claim == 1  # a2

    q2 = rows["qc2"]
    assert q2.claimed == 1
    assert q2.approved == 0 and q2.rejected == 0 and q2.auto_approved_after_claim == 0


async def test_qc_with_no_activity_still_appears_with_zeros():
    qcs = [QcRef(id="idle", email="idle@x.com", products=[Product.PL])]
    uc = GetQcBreakdownUseCase(repo=FakeStatisticsRepo(stats=[], auto_ids=set(), qcs=qcs))
    res = await uc.execute(from_dt=None, to_dt=None, product=None)
    assert len(res.items) == 1
    r = res.items[0]
    assert (r.claimed, r.approved, r.rejected, r.auto_approved_after_claim) == (0, 0, 0, 0)
    assert r.products == [Product.PL]
