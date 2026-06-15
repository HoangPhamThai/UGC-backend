import pytest
from app.modules.reports.data.model import LineItem, ReportStatus
from app.modules.reports.domain.errors import (
    ReportNotFoundError, ReportStateConflictError, ReportValidationError,
)
from app.modules.reports.domain.usecases.upload_article_image import UploadArticleImageUseCase
from app.modules.reports.storage import InMemoryObjectStorage
from tests.reports.fakes import FakeAcceptanceReportRepo
from tests.reports.test_model import _report


def _uc(reports):
    storage = InMemoryObjectStorage()
    return UploadArticleImageUseCase(
        report_repo=FakeAcceptanceReportRepo(reports), storage=storage
    ), storage


def _draft():
    return _report(line_items=[LineItem(article_id="art_1", seq=1, on_air_date="2026-06-01")])


@pytest.mark.asyncio
async def test_upload_stores_image_and_sets_key():
    r = _draft()
    uc, storage = _uc([r])
    updated = await uc.execute(
        report_id=r.id, article_id="art_1",
        image_bytes=b"PNG", content_type="image/png",
        uploader_user_id=r.creator_user_id,
    )
    key = updated.line_items[0].article_image
    assert key is not None
    assert key.endswith(".png")
    assert await storage.get(key) == b"PNG"


@pytest.mark.asyncio
async def test_upload_rejected_for_wrong_creator():
    r = _draft()
    uc, _ = _uc([r])
    with pytest.raises(ReportNotFoundError):
        await uc.execute(
            report_id=r.id, article_id="art_1",
            image_bytes=b"X", content_type="image/png",
            uploader_user_id="other_user",
        )


@pytest.mark.asyncio
async def test_upload_rejected_if_not_draft():
    r = _report(status=ReportStatus.REVIEWING)
    uc, _ = _uc([r])
    with pytest.raises(ReportStateConflictError):
        await uc.execute(
            report_id=r.id, article_id="art_1",
            image_bytes=b"X", content_type="image/png",
            uploader_user_id=r.creator_user_id,
        )


@pytest.mark.asyncio
async def test_upload_rejected_for_unknown_article():
    r = _draft()
    uc, _ = _uc([r])
    with pytest.raises(ReportValidationError):
        await uc.execute(
            report_id=r.id, article_id="art_unknown",
            image_bytes=b"X", content_type="image/png",
            uploader_user_id=r.creator_user_id,
        )


@pytest.mark.asyncio
async def test_upload_jpeg_ext_from_content_type():
    r = _draft()
    uc, _ = _uc([r])
    updated = await uc.execute(
        report_id=r.id, article_id="art_1",
        image_bytes=b"JPEG", content_type="image/jpeg",
        uploader_user_id=r.creator_user_id,
    )
    assert updated.line_items[0].article_image.endswith(".jpg")
