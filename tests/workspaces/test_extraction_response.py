from datetime import date, timedelta

from app.modules.workspaces.data.model import (
    Article,
    ArticleStatus,
    ExtractionStatus,
    PostMetrics,
    Product,
)
from app.modules.workspaces.presentation.schema import ArticleResponse


def test_response_exposes_extraction_status_and_metrics():
    a = Article(
        workspace_id="ws_1",
        name="A",
        product=Product.CL,
        on_air_date=date.today() + timedelta(days=7),
        status=ArticleStatus.APPROVED,
        link="https://www.tiktok.com/@x/photo/1",
        extraction_status=ExtractionStatus.EXTRACTED,
        metrics=PostMetrics(platform="tiktok", views=100),
    )
    r = ArticleResponse.from_model(a)
    assert r.extraction_status == ExtractionStatus.EXTRACTED
    assert r.metrics is not None
    assert r.metrics.views == 100


def test_response_defaults_extraction_when_absent():
    a = Article(
        workspace_id="ws_1",
        name="A",
        product=Product.CL,
        on_air_date=date.today() + timedelta(days=7),
        status=ArticleStatus.NOT_SUBMITTED,
    )
    r = ArticleResponse.from_model(a)
    assert r.extraction_status is None
    assert r.metrics is None
    assert r.extraction_attempts == 0
