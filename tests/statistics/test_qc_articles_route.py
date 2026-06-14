from datetime import date, datetime, timezone

from app.modules.workspaces.data.model import ArticleStatus, Product
from app.modules.statistics.domain.usecases.list_qc_articles import QcArticleEntry
from app.modules.statistics.presentation.schema import QcArticleRowResponse
from app.modules.statistics.presentation.routes import router


def test_qc_article_row_response_maps_outcome_and_epoch_ms():
    entry = QcArticleEntry(
        id="a1", name="X", product=Product.CL, status=ArticleStatus.APPROVED,
        on_air_date=date(2026, 6, 1),
        created_at=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
        creator_email="c@x.com", outcome="approved",
    )
    r = QcArticleRowResponse.from_entry(entry)
    assert isinstance(r.created_at, int)
    assert r.outcome == "approved"
    assert r.creator_email == "c@x.com"


def test_qc_articles_route_is_registered():
    paths = {route.path for route in router.routes}
    assert "/statistics/qcs/{qc_id}/articles" in paths
