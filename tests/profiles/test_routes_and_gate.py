import pytest
from fastapi import HTTPException

from app.modules.profiles.data.model import CreatorProfile, REQUIRED_PROFILE_FIELDS
from app.modules.profiles.presentation.gate import require_profile_complete
from app.modules.profiles.presentation.routes import router
from app.modules.users.data.model import User, UserRole
from tests.profiles.test_usecases import FakeProfileRepo

ALL_REQUIRED = {f: "x" for f in REQUIRED_PROFILE_FIELDS}


def _user(role: UserRole, uid: str = "u_1") -> User:
    qc = [] if role != UserRole.QC else []
    return User(id=uid, email=f"{uid}@x.com", password_hashed="x", role=role, qc_products=qc)


def test_profile_routes_are_registered():
    paths = {r.path for r in router.routes}
    assert "/me/profile" in paths
    assert "/admin/creators/{user_id}/profile" in paths


@pytest.mark.asyncio
async def test_gate_blocks_creator_without_profile():
    repo = FakeProfileRepo()
    with pytest.raises(HTTPException) as ei:
        await require_profile_complete(user=_user(UserRole.CREATOR), profile_repo=repo)
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_gate_blocks_creator_with_incomplete_profile():
    repo = FakeProfileRepo([CreatorProfile(user_id="u_1", full_name="only name")])
    with pytest.raises(HTTPException) as ei:
        await require_profile_complete(user=_user(UserRole.CREATOR), profile_repo=repo)
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_gate_allows_creator_with_complete_profile():
    repo = FakeProfileRepo([CreatorProfile(user_id="u_1", **ALL_REQUIRED)])
    out = await require_profile_complete(user=_user(UserRole.CREATOR), profile_repo=repo)
    assert out.id == "u_1"


@pytest.mark.asyncio
async def test_gate_bypasses_non_creators():
    repo = FakeProfileRepo()  # no profile at all
    out = await require_profile_complete(user=_user(UserRole.ADMIN), profile_repo=repo)
    assert out.role == UserRole.ADMIN
