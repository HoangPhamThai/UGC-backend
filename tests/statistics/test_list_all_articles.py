from app.modules.workspaces.data.model import ArticleStatus
from app.modules.statistics.domain.usecases.list_all_articles import (
    ListAllArticlesUseCase,
)
from tests.conftest import FakeStatisticsRepo, make_article_stat


def _repo():
    stats = [
        make_article_stat(aid="draft", status=ArticleStatus.NOT_SUBMITTED, owner_user_id="u_c1"),
        make_article_stat(aid="a1", status=ArticleStatus.SUBMITTED, owner_user_id="u_c1"),
        make_article_stat(
            aid="a2", status=ArticleStatus.APPROVED, owner_user_id="u_c2",
            claimed_by="u_qc", reviewer_user_id="u_qc",
        ),
    ]
    emails = {"u_c1": "c1@x.com", "u_c2": "c2@x.com", "u_qc": "qc@x.com"}
    return FakeStatisticsRepo(stats=stats, auto_ids=set(), emails=emails)


async def test_excludes_drafts_and_resolves_emails():
    uc = ListAllArticlesUseCase(repo=_repo())
    res = await uc.execute(from_dt=None, to_dt=None, product=None, page=1, limit=20)
    assert res.total == 2  # draft excluded
    ids = {r.id for r in res.items}
    assert ids == {"a1", "a2"}
    a2 = next(r for r in res.items if r.id == "a2")
    assert a2.creator_email == "c2@x.com"
    assert a2.claimed_by_email == "qc@x.com"
    assert a2.reviewer_email == "qc@x.com"
    a1 = next(r for r in res.items if r.id == "a1")
    assert a1.claimed_by_email is None and a1.reviewer_email is None


async def test_pagination():
    uc = ListAllArticlesUseCase(repo=_repo())
    res = await uc.execute(from_dt=None, to_dt=None, product=None, page=1, limit=1)
    assert res.total == 2 and len(res.items) == 1
