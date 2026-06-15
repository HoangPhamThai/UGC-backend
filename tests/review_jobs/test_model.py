from app.modules.review_jobs.data.model import (
    ReviewCard,
    ReviewJob,
    ReviewJobStatus,
)


def test_new_job_defaults_to_parsing_with_no_results():
    job = ReviewJob(article_id="a_1", workspace_id="w_1", owner_user_id="u_qc")
    assert job.id.startswith("rj_")
    assert job.status == ReviewJobStatus.PARSING
    assert job.total is None
    assert job.results == []


def test_card_round_trips_fields():
    card = ReviewCard(
        kind="text-rubric", source="Rubric #1", finding="Too long", location_hint="para 2"
    )
    assert card.model_dump() == {
        "kind": "text-rubric",
        "source": "Rubric #1",
        "finding": "Too long",
        "location_hint": "para 2",
    }
