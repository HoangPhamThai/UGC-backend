from datetime import date, datetime, timezone

from app.modules.workspaces.data.model import ArticleStatus, PostMetrics, Product
from app.modules.statistics.domain.usecases.get_article_detail import (
    ArticleDetailEntry,
)
from app.modules.statistics.presentation.schema import ArticleDetailResponse
from app.modules.statistics.presentation.routes import router


def _entry():
    return ArticleDetailEntry(
        id="art_1", name="X", product=Product.CL, status=ArticleStatus.APPROVED,
        on_air_date=date(2026, 6, 1),
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        link="http://x/art1", link_submitted_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        extraction_status="extracted", has_content=True,
        metrics=PostMetrics(platform="tiktok", views=1500, images=["big"]),
        creator_email="c@x.com", claimed_by_email="qc@x.com", reviewer_email="qc@x.com",
        review_round=2, anchored_feedback_count=3, general_feedback_count=1,
    )


def test_detail_response_maps_entry():
    r = ArticleDetailResponse.from_entry(_entry())
    assert r.id == "art_1"
    assert isinstance(r.created_at, int)
    assert r.link == "http://x/art1"
    assert r.extraction_status == "extracted"
    assert r.has_content is True
    assert r.metrics is not None and r.metrics.views == 1500
    assert not hasattr(r.metrics, "images")
    assert r.review.review_round == 2
    assert r.review.anchored_feedback_count == 3
    assert r.review.general_feedback_count == 1


def test_detail_route_is_registered():
    paths = {route.path for route in router.routes}
    assert "/statistics/articles/{article_id}" in paths
