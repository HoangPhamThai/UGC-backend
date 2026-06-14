from datetime import date, timedelta

from app.modules.workspaces.data.model import (
    Article,
    ArticleStatus,
    ExtractionStatus,
    PostMetrics,
    Product,
)


def _article() -> Article:
    return Article(
        workspace_id="ws_1",
        name="A",
        product=Product.CL,
        on_air_date=date.today() + timedelta(days=7),
        status=ArticleStatus.APPROVED,
    )


def test_extraction_fields_default_empty():
    a = _article()
    assert a.extraction_status is None
    assert a.extraction_attempts == 0
    assert a.extraction_error is None
    assert a.extracted_at is None
    assert a.metrics is None


def test_extraction_status_values():
    assert ExtractionStatus.PENDING.value == "pending"
    assert ExtractionStatus.EXTRACTED.value == "extracted"
    assert ExtractionStatus.FAILED.value == "failed"


def test_post_metrics_accepts_unified_schema_dict():
    data = {
        "platform": "tiktok",
        "url": "https://www.tiktok.com/@x/photo/1",
        "account_name": "@x",
        "nickname": None,
        "created_at": "2026-03-08T01:00:00+00:00",
        "content": "hi",
        "views": 100,
        "favorites": 10,
        "comments": 2,
        "shares": 1,
        "reposts": None,
        "bookmark": 5,
        "images": [],
        "comments_preview": [],
    }
    m = PostMetrics.model_validate(data)
    assert m.platform == "tiktok"
    assert m.views == 100
    assert m.images == []
