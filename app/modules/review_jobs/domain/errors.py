# app/modules/review_jobs/domain/errors.py
class ReviewJobError(Exception):
    """Base class for review-job domain errors."""


class ReviewJobNotFoundError(ReviewJobError):
    """Job does not exist or is not owned by the caller. Maps to 404."""

    def __init__(self, message: str = "Review job not found") -> None:
        super().__init__(message)
