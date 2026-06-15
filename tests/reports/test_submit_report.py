import pytest
from app.modules.reports.data.model import LineItem, ReportStatus
from app.modules.reports.domain.errors import (
    ReportNotFoundError, ReportStateConflictError, ReportValidationError,
)
from app.modules.reports.domain.usecases.submit_report import SubmitReportUseCase
from tests.reports.fakes import FakeAcceptanceReportRepo
from tests.reports.test_model import _report


def _uc(reports):
    return SubmitReportUseCase(report_repo=FakeAcceptanceReportRepo(reports))


@pytest.mark.asyncio
async def test_submit_transitions_to_reviewing():
    r = _report(line_items=[
        LineItem(article_id="art_1", seq=1, on_air_date="2026-06-01", article_image="k/img.jpg")
    ])
    updated = await _uc([r]).execute(report_id=r.id, submitter_user_id=r.creator_user_id)
    assert updated.status == ReportStatus.REVIEWING


@pytest.mark.asyncio
async def test_submit_rejected_for_wrong_creator():
    r = _report(line_items=[
        LineItem(article_id="art_1", seq=1, on_air_date="2026-06-01", article_image="k/img.jpg")
    ])
    with pytest.raises(ReportNotFoundError):
        await _uc([r]).execute(report_id=r.id, submitter_user_id="other")


@pytest.mark.asyncio
async def test_submit_rejected_when_image_missing():
    r = _report(line_items=[
        LineItem(article_id="art_1", seq=1, on_air_date="2026-06-01")  # no image
    ])
    with pytest.raises(ReportValidationError, match="Missing images"):
        await _uc([r]).execute(report_id=r.id, submitter_user_id=r.creator_user_id)


@pytest.mark.asyncio
async def test_submit_rejected_if_already_reviewing():
    r = _report(status=ReportStatus.REVIEWING)
    with pytest.raises(ReportStateConflictError):
        await _uc([r]).execute(report_id=r.id, submitter_user_id=r.creator_user_id)
