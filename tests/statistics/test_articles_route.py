from datetime import date, datetime, timezone

from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.usecases.list_all_articles import ArticleRowEntry
from app.modules.statistics.presentation.schema import ArticleRowResponse
from app.modules.statistics.presentation.routes import router


def test_article_row_response_maps_entry_to_epoch_ms_and_emails():
    entry = ArticleRowEntry(
        id="a1", name="X", product=Product.CL, status=ArticleStatus.APPROVED,
        on_air_date=date(2026, 6, 1),
        created_at=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
        creator_email="c@x.com", claimed_by_email="qc@x.com", reviewer_email=None,
    )
    r = ArticleRowResponse.from_entry(entry)
    assert isinstance(r.created_at, int)
    assert r.creator_email == "c@x.com"
    assert r.claimed_by_email == "qc@x.com"
    assert r.reviewer_email is None


def test_articles_route_is_registered():
    paths = {route.path for route in router.routes}
    assert "/statistics/articles" in paths


def test_article_row_response_includes_link_and_curated_metrics():
    from app.modules.workspaces.data.model import PostMetrics
    entry = ArticleRowEntry(
        id="a1", name="X", product=Product.CL, status=ArticleStatus.APPROVED,
        on_air_date=date(2026, 6, 1),
        created_at=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
        creator_email="c@x.com", claimed_by_email=None, reviewer_email=None,
        link="http://x/a1",
        metrics=PostMetrics(platform="tiktok", views=1500, favorites=4,
                            comments=5, shares=6, images=["big"], content="huge"),
    )
    r = ArticleRowResponse.from_entry(entry)
    assert r.link == "http://x/a1"
    assert r.metrics is not None
    assert r.metrics.views == 1500 and r.metrics.platform == "tiktok"
    assert not hasattr(r.metrics, "images")


def test_article_row_response_null_metrics_is_none():
    entry = ArticleRowEntry(
        id="a1", name="X", product=Product.CL, status=ArticleStatus.SUBMITTED,
        on_air_date=date(2026, 6, 1),
        created_at=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
        creator_email="c@x.com", claimed_by_email=None, reviewer_email=None,
    )
    r = ArticleRowResponse.from_entry(entry)
    assert r.link is None and r.metrics is None
