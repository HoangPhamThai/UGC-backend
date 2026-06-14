from app.modules.reports.domain.errors import (
    ReportError,
    ReportNotFoundError,
    ReportStateConflictError,
    ReportValidationError,
)


def test_hierarchy_and_messages():
    assert issubclass(ReportNotFoundError, ReportError)
    assert issubclass(ReportStateConflictError, ReportError)
    assert issubclass(ReportValidationError, ReportError)
    assert str(ReportNotFoundError()) == "Report not found"
