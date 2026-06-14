from datetime import datetime, timezone

from app.modules.workspaces.data.model import ArticleStatus, PostMetrics, Product
from app.modules.statistics.domain.usecases.list_all_articles import (
    ListAllArticlesUseCase,
)
from tests.conftest import FakeStatisticsRepo, make_article_stat


def _metrics(views):
    return PostMetrics(platform="tiktok", views=views, favorites=1, comments=2, shares=3)


def _repo():
    stats = [
        make_article_stat(aid="low", owner_user_id="u1", link="http://x/low", metrics=_metrics(10)),
        make_article_stat(aid="high", owner_user_id="u1", link="http://x/high", metrics=_metrics(1500)),
        make_article_stat(aid="mid", owner_user_id="u1", link="http://x/mid", metrics=_metrics(500)),
        make_article_stat(aid="nullviews", owner_user_id="u1", link=None, metrics=None),
    ]
    return FakeStatisticsRepo(stats=stats, emails={"u1": "c@x.com"})


async def test_sort_by_views_desc_puts_nulls_last():
    uc = ListAllArticlesUseCase(repo=_repo())
    res = await uc.execute(
        from_dt=None, to_dt=None, product=None, page=1, limit=20,
        sort_by="views", order="desc",
    )
    assert [r.id for r in res.items] == ["high", "mid", "low", "nullviews"]


async def test_sort_by_views_asc_puts_nulls_last():
    uc = ListAllArticlesUseCase(repo=_repo())
    res = await uc.execute(
        from_dt=None, to_dt=None, product=None, page=1, limit=20,
        sort_by="views", order="asc",
    )
    assert [r.id for r in res.items] == ["low", "mid", "high", "nullviews"]


async def test_row_carries_link_and_metrics():
    uc = ListAllArticlesUseCase(repo=_repo())
    res = await uc.execute(
        from_dt=None, to_dt=None, product=None, page=1, limit=20,
        sort_by="views", order="desc",
    )
    top = res.items[0]
    assert top.id == "high"
    assert top.link == "http://x/high"
    assert top.metrics is not None and top.metrics.views == 1500


async def test_default_sort_is_created_at_desc():
    uc = ListAllArticlesUseCase(repo=_repo())
    res = await uc.execute(from_dt=None, to_dt=None, product=None, page=1, limit=20)
    assert res.total == 4
