import pytest

from app.modules.workspaces.data.model import (
    Article, ArticleStatus, ExtractionStatus, PostMetrics, Product,
)
from app.modules.statistics.domain.errors import ArticleNotFoundError
from app.modules.statistics.domain.usecases.get_article_detail import (
    GetArticleDetailUseCase,
)
from tests.conftest import FakeStatisticsRepo
from datetime import date, timedelta


def _article():
    return Article(
        id="art_1", workspace_id="ws_1", name="mua sau tra truoc", product=Product.CL,
        content="<p>body</p>", on_air_date=date.today() + timedelta(days=1),
        status=ArticleStatus.APPROVED, claimed_by="u_qc", reviewer_user_id="u_qc",
        review_round=2, link="http://x/art1",
        extraction_status=ExtractionStatus.EXTRACTED,
        metrics=PostMetrics(platform="tiktok", views=1500, favorites=4, comments=5,
                            shares=6, images=["big"]),
    )


def _repo():
    return FakeStatisticsRepo(
        details={"art_1": (_article(), "u_creator")},
        fb_counts={"art_1": (3, 1)},
        emails={"u_creator": "c@x.com", "u_qc": "qc@x.com"},
    )


async def test_unknown_article_raises():
    uc = GetArticleDetailUseCase(repo=_repo())
    with pytest.raises(ArticleNotFoundError):
        await uc.execute(article_id="nope")


async def test_detail_assembles_fields_and_review_summary():
    uc = GetArticleDetailUseCase(repo=_repo())
    d = await uc.execute(article_id="art_1")
    assert d.id == "art_1"
    assert d.link == "http://x/art1"
    assert d.has_content is True
    assert d.extraction_status == "extracted"
    assert d.creator_email == "c@x.com"
    assert d.claimed_by_email == "qc@x.com"
    assert d.reviewer_email == "qc@x.com"
    assert d.metrics is not None and d.metrics.views == 1500
    assert d.review_round == 2
    assert d.anchored_feedback_count == 3
    assert d.general_feedback_count == 1
