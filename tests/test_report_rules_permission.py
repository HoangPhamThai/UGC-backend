from app.core.permissions import (
    INTERIM_ALLOWED_PERMISSIONS, Permission, ROLE_PERMISSIONS, interim_key_allows,
)
from app.modules.users.data.model import UserRole


def test_admin_has_rule_jobs_write():
    assert Permission.REPORT_RULE_JOBS_WRITE in ROLE_PERMISSIONS[UserRole.ADMIN]


def test_rule_jobs_write_is_interim_allowed():
    assert Permission.REPORT_RULE_JOBS_WRITE in INTERIM_ALLOWED_PERMISSIONS
    assert interim_key_allows([Permission.REPORT_RULE_JOBS_WRITE]) is True
