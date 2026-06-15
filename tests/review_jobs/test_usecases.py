from datetime import datetime, timezone

import pytest

from app.modules.review_jobs.data.model import ReviewCard, ReviewJobStatus
from app.modules.review_jobs.domain.errors import ReviewJobNotFoundError
from app.modules.review_jobs.domain.usecases.create_job import CreateReviewJobUseCase
from app.modules.review_jobs.domain.usecases.get_job import GetReviewJobUseCase
from app.modules.review_jobs.domain.usecases.get_latest_job import (
    GetLatestReviewJobUseCase,
)
from app.modules.review_jobs.domain.usecases.update_job import (
    AppendResultUseCase,
    FinalizeJobUseCase,
    SetTotalUseCase,
)
from tests.conftest import FakeReviewJobRepo, make_review_job


async def test_create_sets_owner_and_parsing_status():
    repo = FakeReviewJobRepo()
    uc = CreateReviewJobUseCase(repo=repo)
    job = await uc.execute(owner_user_id="u_qc", article_id="a_1", workspace_id="w_1")
    assert job.owner_user_id == "u_qc"
    assert job.status == ReviewJobStatus.PARSING
    assert repo.items[job.id] is job


async def test_create_stores_rubrics():
    repo = FakeReviewJobRepo()
    uc = CreateReviewJobUseCase(repo=repo)
    job = await uc.execute(
        owner_user_id="u_qc", article_id="a_1", workspace_id="w_1", rubrics="be concise"
    )
    assert job.rubrics == "be concise"
    assert repo.items[job.id].rubrics == "be concise"


async def test_get_latest_returns_most_recent_for_caller_and_article():
    older = make_review_job(jid="rj_old", owner_user_id="u_qc", article_id="a_1")
    newer = make_review_job(jid="rj_new", owner_user_id="u_qc", article_id="a_1")
    older.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer.created_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    repo = FakeReviewJobRepo([older, newer])
    uc = GetLatestReviewJobUseCase(repo=repo)
    job = await uc.execute(caller_id="u_qc", article_id="a_1")
    assert job is not None and job.id == "rj_new"


async def test_get_latest_returns_none_when_no_job():
    repo = FakeReviewJobRepo()
    uc = GetLatestReviewJobUseCase(repo=repo)
    assert await uc.execute(caller_id="u_qc", article_id="a_1") is None


async def test_get_latest_does_not_leak_other_owner_or_article():
    other_owner = make_review_job(jid="rj_o", owner_user_id="u_other", article_id="a_1")
    other_article = make_review_job(jid="rj_a", owner_user_id="u_qc", article_id="a_2")
    repo = FakeReviewJobRepo([other_owner, other_article])
    uc = GetLatestReviewJobUseCase(repo=repo)
    assert await uc.execute(caller_id="u_qc", article_id="a_1") is None


async def test_set_total_flips_to_evaluating():
    repo = FakeReviewJobRepo([make_review_job(jid="rj_1")])
    uc = SetTotalUseCase(repo=repo)
    job = await uc.execute(job_id="rj_1", total=7)
    assert job.total == 7 and job.status == ReviewJobStatus.EVALUATING


async def test_append_result_accumulates():
    repo = FakeReviewJobRepo([make_review_job(jid="rj_1")])
    uc = AppendResultUseCase(repo=repo)
    card = ReviewCard(kind="text-rubric", source="R1", finding="x")
    job = await uc.execute(job_id="rj_1", card=card)
    assert len(job.results) == 1 and job.results[0].finding == "x"


async def test_finalize_sets_terminal_status():
    repo = FakeReviewJobRepo([make_review_job(jid="rj_1")])
    uc = FinalizeJobUseCase(repo=repo)
    job = await uc.execute(job_id="rj_1", status=ReviewJobStatus.DONE)
    assert job.status == ReviewJobStatus.DONE


async def test_update_missing_job_raises():
    repo = FakeReviewJobRepo()
    with pytest.raises(ReviewJobNotFoundError):
        await SetTotalUseCase(repo=repo).execute(job_id="missing", total=1)


async def test_get_owner_ok_and_nonowner_404():
    repo = FakeReviewJobRepo([make_review_job(jid="rj_1", owner_user_id="u_qc")])
    uc = GetReviewJobUseCase(repo=repo)
    assert (await uc.execute(job_id="rj_1", caller_id="u_qc")).id == "rj_1"
    with pytest.raises(ReviewJobNotFoundError):
        await uc.execute(job_id="rj_1", caller_id="u_intruder")
    with pytest.raises(ReviewJobNotFoundError):
        await uc.execute(job_id="missing", caller_id="u_qc")
