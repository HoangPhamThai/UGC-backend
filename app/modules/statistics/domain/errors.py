# app/modules/statistics/domain/errors.py
class StatisticsError(Exception):
    """Base class for statistics-domain errors."""


class CreatorNotFoundError(StatisticsError):
    """The requested creator id does not exist or is not a creator. Maps to 404."""

    def __init__(self, message: str = "Creator not found") -> None:
        super().__init__(message)


class QcNotFoundError(StatisticsError):
    """The requested QC id does not exist or is not a QC. Maps to 404."""

    def __init__(self, message: str = "QC not found") -> None:
        super().__init__(message)


class ArticleNotFoundError(StatisticsError):
    """The requested article id does not exist. Maps to 404."""

    def __init__(self, message: str = "Article not found") -> None:
        super().__init__(message)
