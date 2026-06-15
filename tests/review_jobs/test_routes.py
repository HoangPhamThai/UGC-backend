import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.core.auth import get_current_principal
from app.modules.review_jobs.presentation import deps
from tests.conftest import FakeReviewJobRepo, make_review_job, make_user


def _qc(uid="u_qc"):
    # make_user defaults to role=QC and supplies the required qc_products.
    return make_user(uid=uid)


@pytest.fixture
def repo_and_client():
    repo = FakeReviewJobRepo([make_review_job(jid="rj_1", owner_user_id="u_qc")])
    app.dependency_overrides[deps.get_review_job_repo] = lambda: repo
    app.dependency_overrides[get_current_principal] = lambda: _qc()
    # bypass permission dependency layers by overriding the principal/user resolution
    yield repo, TestClient(app)
    app.dependency_overrides.clear()


def test_get_job_returns_progress(repo_and_client):
    repo, client = repo_and_client
    res = client.get("/api/v1/review-jobs/rj_1")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "parsing"
    assert body["data"]["progress"] == "0/?"


def test_get_job_nonowner_404(repo_and_client):
    repo, client = repo_and_client
    app.dependency_overrides[get_current_principal] = lambda: _qc("u_other")
    res = client.get("/api/v1/review-jobs/rj_1")
    assert res.status_code == 404
    assert res.json()["success"] is False
