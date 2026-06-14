from datetime import date, timedelta

from app.modules.workspaces.data.model import Article, ArticleStatus, Product
from app.modules.workspaces.presentation.routes import router
from app.modules.workspaces.presentation.schema import ArticleResponse


def test_link_route_is_registered():
    paths = {r.path for r in router.routes}
    assert "/workspaces/{workspace_id}/articles/{article_id}/link" in paths


def test_article_response_includes_link_fields():
    a = Article(
        workspace_id="ws_1",
        name="A",
        product=Product.CL,
        on_air_date=date.today() + timedelta(days=7),
        status=ArticleStatus.APPROVED,
        link="https://www.tiktok.com/@x/photo/1",
        link_edit_count=2,
        report_id=None,
    )
    r = ArticleResponse.from_model(a)
    assert r.link == "https://www.tiktok.com/@x/photo/1"
    assert r.link_edit_count == 2
    assert r.report_id is None
