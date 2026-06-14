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
