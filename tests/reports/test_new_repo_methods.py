import pytest
from app.modules.reports.data.model import LineItem, ReportStatus
from tests.reports.fakes import FakeAcceptanceReportRepo
from tests.reports.test_model import _report


@pytest.mark.asyncio
async def test_update_line_item_image_sets_key():
    r = _report(line_items=[LineItem(article_id="art_1", seq=1, on_air_date="2026-06-01")])
    repo = FakeAcceptanceReportRepo([r])
    updated = await repo.update_line_item_image(r.id, "art_1", "reports/k.jpg")
    assert updated is not None
    assert updated.line_items[0].article_image == "reports/k.jpg"


@pytest.mark.asyncio
async def test_update_line_item_image_returns_none_for_missing():
    repo = FakeAcceptanceReportRepo([])
    assert await repo.update_line_item_image("nope", "art_1", "k.jpg") is None


@pytest.mark.asyncio
async def test_submit_transitions_draft_to_reviewing():
    r = _report()
    repo = FakeAcceptanceReportRepo([r])
    updated = await repo.submit(r.id)
    assert updated is not None
    assert updated.status == ReportStatus.REVIEWING


@pytest.mark.asyncio
async def test_approve_transitions_reviewing_to_final():
    r = _report(status=ReportStatus.REVIEWING)
    repo = FakeAcceptanceReportRepo([r])
    updated = await repo.approve(r.id, approved_by="u_admin")
    assert updated is not None
    assert updated.status == ReportStatus.FINAL
    assert updated.finalized_by == "u_admin"


@pytest.mark.asyncio
async def test_get_by_creator_period_finds_reviewing():
    r = _report(status=ReportStatus.REVIEWING)
    repo = FakeAcceptanceReportRepo([r])
    found = await repo.get_by_creator_period(r.creator_user_id, r.period)
    assert found is not None
    assert found.status == ReportStatus.REVIEWING
