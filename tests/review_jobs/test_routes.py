from datetime import datetime, timezone

import httpx
import pytest

from app.app import app
from app.core.auth import get_current_principal
from app.modules.review_jobs.data.model import ReviewCard, ReviewJobStatus
from app.modules.review_jobs.presentation import deps
from tests.conftest import FakeReviewJobRepo, make_review_job, make_user

# NOTE: This repo's test suite does not use Starlette's TestClient because the
# installed httpx 0.28 dropped the `app=` kwarg that starlette 0.36's TestClient
# relies on. We exercise the ASGI app directly via httpx.ASGITransport instead,
# which is the modern equivalent and works under `asyncio_mode = auto`.


def _qc(uid="u_qc"):
    # make_user defaults to role=QC and supplies the required qc_products.
    return make_user(uid=uid)


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


@pytest.fixture
def repo():
    r = FakeReviewJobRepo([make_review_job(jid="rj_1", owner_user_id="u_qc")])
    app.dependency_overrides[deps.get_review_job_repo] = lambda: r
    app.dependency_overrides[get_current_principal] = lambda: _qc()
    # Overriding get_current_principal lets require_permissions pass without auth headers.
    yield r
    app.dependency_overrides.clear()


async def test_get_job_returns_progress(repo):
    res = await _get("/api/v1/review-jobs/rj_1")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "parsing"
    assert body["data"]["progress"] == "0/?"


async def test_get_job_nonowner_404(repo):
    app.dependency_overrides[get_current_principal] = lambda: _qc("u_other")
    res = await _get("/api/v1/review-jobs/rj_1")
    assert res.status_code == 404
    assert res.json()["success"] is False


async def test_get_latest_returns_job_data(repo):
    job = make_review_job(jid="rj_latest", owner_user_id="u_qc", article_id="a_1")
    job.created_at = datetime(2026, 12, 31, tzinfo=timezone.utc)
    job.rubrics = "be concise"
    job.status = ReviewJobStatus.DONE
    job.total = 1
    job.results = [ReviewCard(kind="text-rubric", source="R1", finding="x")]
    await repo.create(job)
    res = await _get("/api/v1/review-jobs/latest?workspace_id=w_1&article_id=a_1")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["rubrics"] == "be concise"
    assert body["data"]["status"] == "done"
    assert [c["finding"] for c in body["data"]["results"]] == ["x"]


async def test_get_latest_returns_null_when_none(repo):
    res = await _get("/api/v1/review-jobs/latest?workspace_id=w_1&article_id=a_nope")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"] is None
