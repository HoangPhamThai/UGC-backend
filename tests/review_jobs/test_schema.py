from app.modules.review_jobs.data.model import ReviewCard, ReviewJob, ReviewJobStatus
from app.modules.review_jobs.presentation.schema import ReviewJobResponse


def test_response_progress_and_completed_from_results():
    job = ReviewJob(article_id="a_1", workspace_id="w_1", owner_user_id="u_qc")
    job.status = ReviewJobStatus.EVALUATING
    job.total = 3
    job.results = [
        ReviewCard(kind="text-rubric", source="R1", finding="a"),
        ReviewCard(kind="text-rubric", source="R2", finding="b"),
    ]
    resp = ReviewJobResponse.from_job(job)
    assert resp.status == "evaluating"
    assert resp.completed == 2
    assert resp.total == 3
    assert resp.progress == "2/3"
    assert [c.finding for c in resp.results] == ["a", "b"]


def test_response_includes_rubrics():
    job = ReviewJob(
        article_id="a_1", workspace_id="w_1", owner_user_id="u_qc", rubrics="rubric text"
    )
    resp = ReviewJobResponse.from_job(job)
    assert resp.rubrics == "rubric text"


def test_response_progress_when_total_unknown():
    job = ReviewJob(article_id="a_1", workspace_id="w_1", owner_user_id="u_qc")
    resp = ReviewJobResponse.from_job(job)
    assert resp.status == "parsing"
    assert resp.total is None
    assert resp.completed == 0
    assert resp.progress == "0/?"
