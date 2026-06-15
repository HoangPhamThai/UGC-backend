from pathlib import Path

import pytest

from app.modules.reports.domain.errors import ReportValidationError
from app.modules.reports.domain.usecases.template import (
    DownloadTemplateUseCase,
    GetTemplateUseCase,
    UploadTemplateUseCase,
)
from app.modules.reports.rendering import TEMPLATE_PATH
from tests.reports.fakes import FakeTemplateRepo


@pytest.mark.asyncio
async def test_get_template_reports_default_when_none_uploaded():
    meta = await GetTemplateUseCase(template_repo=FakeTemplateRepo()).execute()
    assert meta.is_default is True


@pytest.mark.asyncio
async def test_upload_rejects_invalid_then_accepts_valid():
    repo = FakeTemplateRepo()
    uc = UploadTemplateUseCase(template_repo=repo)
    with pytest.raises(ReportValidationError):
        await uc.execute(data=b"nope", filename="x.docx", uploaded_by="u_admin")

    valid = Path(TEMPLATE_PATH).read_bytes()
    meta = await uc.execute(data=valid, filename="tpl.docx", uploaded_by="u_admin")
    assert meta.is_default is False and meta.filename == "tpl.docx"


@pytest.mark.asyncio
async def test_download_returns_default_bytes_when_none_uploaded():
    filename, data = await DownloadTemplateUseCase(template_repo=FakeTemplateRepo()).execute()
    assert data == Path(TEMPLATE_PATH).read_bytes()
    assert filename.endswith(".docx")
