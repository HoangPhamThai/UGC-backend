import pytest

from app.modules.workspaces.data.model import ArticleStatus
from tests.conftest import FakeArticleRepo, make_article


@pytest.mark.asyncio
async def test_set_and_clear_report_id():
    art = make_article(status=ArticleStatus.APPROVED, aid="art_1")
    repo = FakeArticleRepo([art])
    locked = await repo.set_report_id("art_1", "rpt_1")
    assert locked.report_id == "rpt_1"
    unlocked = await repo.set_report_id("art_1", None)
    assert unlocked.report_id is None


@pytest.mark.asyncio
async def test_set_report_id_missing_returns_none():
    repo = FakeArticleRepo([])
    assert await repo.set_report_id("nope", "rpt_1") is None
