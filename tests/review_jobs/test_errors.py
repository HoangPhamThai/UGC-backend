from app.modules.review_jobs.domain.errors import (
    ReviewJobError,
    ReviewJobNotFoundError,
)


def test_not_found_is_a_review_job_error():
    err = ReviewJobNotFoundError()
    assert isinstance(err, ReviewJobError)
    assert str(err) == "Review job not found"
