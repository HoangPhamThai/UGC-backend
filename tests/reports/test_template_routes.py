# tests/reports/test_template_routes.py
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_principal
from app.modules.reports.presentation import routes
from app.modules.reports.presentation.deps import (
    get_uc_download_template,
    get_uc_get_template,
    get_uc_upload_template,
)
from app.modules.reports.domain.usecases.template import (
    DownloadTemplateUseCase,
    GetTemplateUseCase,
    UploadTemplateUseCase,
)
from app.modules.reports.rendering import TEMPLATE_PATH
from app.modules.users.data.model import User, UserRole
from tests.reports.fakes import FakeTemplateRepo


def _fake_admin():
    return User(
        _id="u_admin",
        email="admin@test.com",
        password_hashed="x",
        role=UserRole.ADMIN,
    )


def _app(repo: FakeTemplateRepo) -> FastAPI:
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    # Override the root auth dependency — all require_permissions(...) closures
    # call Depends(get_current_principal), so this single override bypasses auth.
    app.dependency_overrides[get_current_principal] = lambda: _fake_admin()
    app.dependency_overrides[get_uc_get_template] = lambda: GetTemplateUseCase(template_repo=repo)
    app.dependency_overrides[get_uc_upload_template] = lambda: UploadTemplateUseCase(template_repo=repo)
    app.dependency_overrides[get_uc_download_template] = lambda: DownloadTemplateUseCase(template_repo=repo)
    return app


@pytest.mark.asyncio
async def test_get_template_meta_defaults_to_is_default_true():
    app = _app(FakeTemplateRepo())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        res = await client.get("/api/v1/reports/template")
    assert res.status_code == 200
    assert res.json()["data"]["is_default"] is True


@pytest.mark.asyncio
async def test_upload_template_accepts_valid_docx():
    repo = FakeTemplateRepo()
    app = _app(repo)
    transport = ASGITransport(app=app)
    data = Path(TEMPLATE_PATH).read_bytes()
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        res = await client.post(
            "/api/v1/reports/template",
            files={
                "file": (
                    "tpl.docx",
                    data,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert res.status_code == 200
    assert res.json()["data"]["is_default"] is False


@pytest.mark.asyncio
async def test_download_template_returns_docx_bytes():
    repo = FakeTemplateRepo()
    app = _app(repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        res = await client.get("/api/v1/reports/template/download")
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument" in res.headers["content-type"]
