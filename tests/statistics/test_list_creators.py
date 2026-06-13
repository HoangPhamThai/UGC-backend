from datetime import datetime, timezone

from app.modules.workspaces.data.model import ArticleStatus
from app.modules.statistics.domain.repo import CreatorRef
from app.modules.statistics.domain.usecases.list_creators import ListCreatorsUseCase
from tests.conftest import FakeStatisticsRepo, make_article_stat


def _repo():
    creators = [
        CreatorRef(id="c_b", email="bob@x.com"),
        CreatorRef(id="c_a", email="ann@x.com"),
        CreatorRef(id="c_z", email="zoe@x.com"),  # no articles
    ]
    stats = [
        make_article_stat(aid="a1", owner_user_id="c_a", status=ArticleStatus.SUBMITTED),
        make_article_stat(aid="a2", owner_user_id="c_a", status=ArticleStatus.APPROVED),
        make_article_stat(aid="b1", owner_user_id="c_b", status=ArticleStatus.REJECTED),
    ]
    return FakeStatisticsRepo(stats=stats, creators=creators)


async def test_no_time_filter_lists_all_creators_sorted_with_total_counts():
    uc = ListCreatorsUseCase(repo=_repo())
    res = await uc.execute(q=None, from_dt=None, to_dt=None, product=None, page=1, limit=10)
    # sorted by email asc: ann, bob, zoe
    assert [c.email for c in res.items] == ["ann@x.com", "bob@x.com", "zoe@x.com"]
    counts = {c.id: c.article_count_in_window for c in res.items}
    assert counts == {"c_a": 2, "c_b": 1, "c_z": 0}
    assert res.total == 3


async def test_time_filter_restricts_to_creators_with_articles():
    # Any time bound activates the "must have >=1 article in window" restriction.
    uc = ListCreatorsUseCase(repo=_repo())
    res = await uc.execute(
        q=None,
        from_dt=datetime(2000, 1, 1, tzinfo=timezone.utc),
        to_dt=None,
        product=None,
        page=1,
        limit=10,
    )
    assert {c.id for c in res.items} == {"c_a", "c_b"}  # c_z excluded
    assert res.total == 2


async def test_search_by_email_substring():
    uc = ListCreatorsUseCase(repo=_repo())
    res = await uc.execute(q="ANN", from_dt=None, to_dt=None, product=None, page=1, limit=10)
    assert [c.email for c in res.items] == ["ann@x.com"]
    assert res.total == 1


async def test_pagination():
    uc = ListCreatorsUseCase(repo=_repo())
    page1 = await uc.execute(q=None, from_dt=None, to_dt=None, product=None, page=1, limit=2)
    page2 = await uc.execute(q=None, from_dt=None, to_dt=None, product=None, page=2, limit=2)
    assert [c.email for c in page1.items] == ["ann@x.com", "bob@x.com"]
    assert [c.email for c in page2.items] == ["zoe@x.com"]
    assert page1.total == 3 and page2.total == 3
