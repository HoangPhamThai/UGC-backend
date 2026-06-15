from app.core.permissions import (
    INTERIM_ALLOWED_PERMISSIONS,
    Permission,
    ROLE_PERMISSIONS,
    interim_key_allows,
)
from app.modules.users.data.model import UserRole


def test_review_jobs_write_permission_exists():
    assert Permission.REVIEW_JOBS_WRITE.value == "review_jobs:write"


def test_qc_and_admin_have_review_jobs_write():
    assert Permission.REVIEW_JOBS_WRITE in ROLE_PERMISSIONS[UserRole.QC]
    assert Permission.REVIEW_JOBS_WRITE in ROLE_PERMISSIONS[UserRole.ADMIN]


def test_creator_does_not_have_review_jobs_write():
    assert Permission.REVIEW_JOBS_WRITE not in ROLE_PERMISSIONS[UserRole.CREATOR]


def test_review_jobs_write_is_interim_allowed():
    assert Permission.REVIEW_JOBS_WRITE in INTERIM_ALLOWED_PERMISSIONS
    assert interim_key_allows([Permission.REVIEW_JOBS_WRITE]) is True
