from app.core.permissions import Permission, ROLE_PERMISSIONS
from app.modules.users.data.model import UserRole


def test_reports_manage_granted_to_admin_and_superuser_only():
    assert Permission.REPORTS_MANAGE in ROLE_PERMISSIONS[UserRole.ADMIN]
    assert Permission.REPORTS_MANAGE in ROLE_PERMISSIONS[UserRole.SUPERUSER]
    assert Permission.REPORTS_MANAGE not in ROLE_PERMISSIONS[UserRole.CREATOR]
    assert Permission.REPORTS_MANAGE not in ROLE_PERMISSIONS[UserRole.QC]
