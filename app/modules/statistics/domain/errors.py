# app/modules/statistics/domain/errors.py
class StatisticsError(Exception):
    """Base class for statistics-domain errors."""


class CreatorNotFoundError(StatisticsError):
    """The requested creator id does not exist or is not a creator. Maps to 404."""

    def __init__(self, message: str = "Creator not found") -> None:
        super().__init__(message)
