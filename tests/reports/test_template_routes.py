# tests/reports/test_template_routes.py
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_current_principal
from app.core.errors import register_exception_handlers
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
    register_exception_handlers(app)
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
async def test_upload_template_disabled_in_demo():
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
    # Upload is disabled in the DEMO build: the request is refused with the
    # standard error envelope and the stored template is left untouched.
    assert res.status_code == 403
    body = res.json()
    assert body["success"] is False
    assert body["message"] == (
        "Sorry, this feature is not supported for DEMO. It will be available in production."
    )
    assert repo._bytes is None


@pytest.mark.asyncio
async def test_download_template_returns_docx_bytes():
    repo = FakeTemplateRepo()
    app = _app(repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        res = await client.get("/api/v1/reports/template/download")
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument" in res.headers["content-type"]
