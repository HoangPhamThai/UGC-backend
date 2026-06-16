from app.modules.reports.presentation.deps import (
    get_uc_approve_report,
    get_uc_generate_reports,
)


def test_generate_uc_has_email_service():
    uc = get_uc_generate_reports()
    assert uc.email_service is not None


def test_approve_uc_has_email_service():
    uc = get_uc_approve_report()
    assert uc.email_service is not None
