# app/modules/reports/domain/errors.py
class ReportError(Exception):
    """Base class for acceptance-report domain errors."""


class ReportNotFoundError(ReportError):
    """Report does not exist or is out of the caller's scope. Maps to 404."""

    def __init__(self, message: str = "Report not found") -> None:
        super().__init__(message)


class ReportStateConflictError(ReportError):
    """Operation not allowed in the report's current state (e.g. finalize a
    non-draft, delete a final, profile incomplete). Maps to 409."""

    def __init__(self, message: str = "Report is not in a valid state for this operation") -> None:
        super().__init__(message)


class ReportValidationError(ReportError):
    """Request data failed a business rule (e.g. bad period, negative price).
    Maps to 400."""

    def __init__(self, message: str = "Invalid report request") -> None:
        super().__init__(message)
