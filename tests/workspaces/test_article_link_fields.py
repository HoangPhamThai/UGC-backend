from datetime import date, timedelta

from app.modules.workspaces.data.model import Article, ArticleStatus, MAX_LINK_EDITS, Product


def _article() -> Article:
    return Article(
        workspace_id="ws_1",
        name="A",
        product=Product.CL,
        on_air_date=date.today() + timedelta(days=7),
        status=ArticleStatus.APPROVED,
    )


def test_link_fields_default_empty():
    a = _article()
    assert a.link is None
    assert a.link_submitted_at is None
    assert a.link_edit_count == 0
    assert a.report_id is None


def test_max_link_edits_is_five():
    assert MAX_LINK_EDITS == 5
