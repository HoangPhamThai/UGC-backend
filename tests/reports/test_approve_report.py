import pytest

from app.modules.profiles.data.model import REQUIRED_PROFILE_FIELDS
from app.modules.reports.data.model import LineItem, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError, ReportStateConflictError
from app.modules.reports.domain.usecases.approve_report import ApproveReportUseCase
from app.modules.reports.storage import InMemoryObjectStorage
from tests.reports.fakes import FakeAcceptanceReportRepo, FakeTemplateRepo, RecordingEmailService
from tests.reports.test_model import _report

ALL_REQUIRED = {f: "x" for f in REQUIRED_PROFILE_FIELDS}


def _reviewing():
    return _report(
        status=ReportStatus.REVIEWING,
        creator_snapshot={**ALL_REQUIRED},
        line_items=[
            LineItem(
                article_id="art_1", seq=1, on_air_date="2026-06-01",
                article_image="reports/2026-06/rpt_1/images/art_1.jpg",
            )
        ],
    )


def _make_uc(reports, captured=None, email_service=None):
    storage = InMemoryObjectStorage()

    def fake_render(*, scalars, line_items, template_bytes=None, line_item_images=None):
        if captured is not None:
            captured.append({"line_item_images": line_item_images})
        return b"DOCX-WITH-IMAGES"

    return ApproveReportUseCase(
        report_repo=FakeAcceptanceReportRepo(reports),
        storage=storage,
        render=fake_render,
        template_repo=FakeTemplateRepo(),
        email_service=email_service,
    ), storage


@pytest.mark.asyncio
async def test_approve_transitions_to_final_and_stores_docx():
    r = _reviewing()
    uc, storage = _make_uc([r])
    await storage.put(r.line_items[0].article_image, b"IMG", content_type="image/jpeg")

    approved = await uc.execute(report_id=r.id, approved_by="u_admin")
    assert approved.status == ReportStatus.FINAL
    assert approved.finalized_by == "u_admin"
    assert await storage.get(r.object_key) == b"DOCX-WITH-IMAGES"


@pytest.mark.asyncio
async def test_approve_passes_image_bytes_to_render():
    r = _reviewing()
    captured = []
    uc, storage = _make_uc([r], captured=captured)
    await storage.put(r.line_items[0].article_image, b"IMG_BYTES", content_type="image/jpeg")

    await uc.execute(report_id=r.id, approved_by="u_admin")
    assert captured[0]["line_item_images"] == {"art_1": b"IMG_BYTES"}


@pytest.mark.asyncio
async def test_approve_rejected_for_non_reviewing():
    r = _report(creator_snapshot={**ALL_REQUIRED})
    uc, _ = _make_uc([r])
    with pytest.raises(ReportStateConflictError):
        await uc.execute(report_id=r.id, approved_by="u_admin")


@pytest.mark.asyncio
async def test_approve_rejected_for_incomplete_profile():
    r = _report(status=ReportStatus.REVIEWING, creator_snapshot={})
    uc, _ = _make_uc([r])
    with pytest.raises(ReportStateConflictError, match="incomplete"):
        await uc.execute(report_id=r.id, approved_by="u_admin")


@pytest.mark.asyncio
async def test_approve_schedules_approved_email():
    from app.modules.email.messages import ReportEmailEvent
    r = _reviewing()
    email = RecordingEmailService()
    uc, storage = _make_uc([r], email_service=email)
    await storage.put(r.line_items[0].article_image, b"IMG", content_type="image/jpeg")

    await uc.execute(report_id=r.id, approved_by="u_admin")
    assert email.report_events == [(ReportEmailEvent.APPROVED, r.period, r.creator_user_id)]


@pytest.mark.asyncio
async def test_approve_non_reviewing_does_not_schedule_email():
    r = _report(creator_snapshot={**ALL_REQUIRED})
    email = RecordingEmailService()
    uc, _ = _make_uc([r], email_service=email)
    with pytest.raises(ReportStateConflictError):
        await uc.execute(report_id=r.id, approved_by="u_admin")
    assert email.report_events == []
