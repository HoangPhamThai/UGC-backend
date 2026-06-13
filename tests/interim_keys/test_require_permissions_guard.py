import pytest
from fastapi import HTTPException

from app.core.permissions import Permission, require_permissions
from app.modules.users.data.model import UserRole
from tests.conftest import make_user


class _Req:
    class _State:
        def __init__(self, is_interim):
            self.is_interim = is_interim

    def __init__(self, is_interim):
        self.state = _Req._State(is_interim)


def test_admin_jwt_allowed_for_stats_read():
    admin = make_user(role=UserRole.ADMIN, uid="u_admin")
    dep = require_permissions(Permission.STATS_READ)
    assert dep(_Req(is_interim=False), user=admin) is admin


def test_interim_allowed_for_stats_read():
    admin = make_user(role=UserRole.ADMIN, uid="u_admin")
    dep = require_permissions(Permission.STATS_READ)
    assert dep(_Req(is_interim=True), user=admin) is admin


def test_interim_blocked_for_mutation_permission():
    admin = make_user(role=UserRole.ADMIN, uid="u_admin")
    dep = require_permissions(Permission.USERS_CREATE_QC)
    with pytest.raises(HTTPException) as ei:
        dep(_Req(is_interim=True), user=admin)
    assert ei.value.status_code == 403


def test_jwt_admin_still_allowed_for_mutation_permission():
    admin = make_user(role=UserRole.ADMIN, uid="u_admin")
    dep = require_permissions(Permission.USERS_CREATE_QC)
    assert dep(_Req(is_interim=False), user=admin) is admin
