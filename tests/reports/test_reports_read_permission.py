from app.core.permissions import (
    INTERIM_ALLOWED_PERMISSIONS,
    Permission,
    ROLE_PERMISSIONS,
)
from app.modules.users.data.model import UserRole


def test_reports_read_granted_to_admin_and_superuser():
    assert Permission.REPORTS_READ in ROLE_PERMISSIONS[UserRole.ADMIN]
    assert Permission.REPORTS_READ in ROLE_PERMISSIONS[UserRole.SUPERUSER]
    assert Permission.REPORTS_READ not in ROLE_PERMISSIONS[UserRole.QC]


def test_reports_read_is_interim_allowed_but_manage_is_not():
    assert Permission.REPORTS_READ in INTERIM_ALLOWED_PERMISSIONS
    assert Permission.REPORTS_MANAGE not in INTERIM_ALLOWED_PERMISSIONS
