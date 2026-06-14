import pytest

from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.errors import QcNotFoundError
from app.modules.statistics.domain.repo import QcRef
from app.modules.statistics.domain.usecases.list_qc_articles import (
    ListQcArticlesUseCase,
)
from tests.conftest import FakeStatisticsRepo, make_article_stat


def _repo():
    stats = [
        make_article_stat(aid="claimed_only", status=ArticleStatus.SUBMITTED, owner_user_id="u_c1", claimed_by="u_qc"),
        make_article_stat(aid="approved", status=ArticleStatus.APPROVED, owner_user_id="u_c1", claimed_by="u_qc", reviewer_user_id="u_qc"),
        make_article_stat(aid="rejected", status=ArticleStatus.REJECTED, owner_user_id="u_c2", claimed_by="u_qc", rejected_by="u_qc"),
        make_article_stat(aid="auto", status=ArticleStatus.APPROVED, owner_user_id="u_c2", claimed_by="u_qc"),
        # creator re-submitted after feedback; QC still claimed -> in_review
        make_article_stat(aid="edited", status=ArticleStatus.EDITED, owner_user_id="u_c1", claimed_by="u_qc"),
        make_article_stat(aid="other_qc", status=ArticleStatus.APPROVED, owner_user_id="u_c1", claimed_by="u_other"),
    ]
    qcs = [QcRef(id="u_qc", email="qc@x.com", products=[Product.CL])]
    emails = {"u_c1": "c1@x.com", "u_c2": "c2@x.com"}
    return FakeStatisticsRepo(stats=stats, auto_ids={"auto"}, qcs=qcs, emails=emails)


async def test_unknown_qc_raises():
    uc = ListQcArticlesUseCase(repo=_repo())
    with pytest.raises(QcNotFoundError):
        await uc.execute(qc_id="nope", from_dt=None, to_dt=None, product=None, page=1, limit=20)


async def test_only_claimed_by_qc_with_outcomes():
    uc = ListQcArticlesUseCase(repo=_repo())
    res = await uc.execute(qc_id="u_qc", from_dt=None, to_dt=None, product=None, page=1, limit=20)
    assert res.total == 5  # other_qc excluded
    outcome = {r.id: r.outcome for r in res.items}
    assert outcome == {
        "claimed_only": "in_review",
        "approved": "approved",
        "rejected": "rejected",
        "auto": "auto_approved",
        "edited": "in_review",
    }
    by_id = {r.id: r for r in res.items}
    assert by_id["approved"].creator_email == "c1@x.com"
