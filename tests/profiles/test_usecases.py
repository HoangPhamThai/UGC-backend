from typing import Optional

import pytest

from app.modules.profiles.data.model import CreatorProfile, REQUIRED_PROFILE_FIELDS
from app.modules.profiles.domain.repo import CreatorProfileRepo
from app.modules.profiles.domain.usecases.get_my_profile import GetMyProfileUseCase
from app.modules.profiles.domain.usecases.upsert_my_profile import UpsertMyProfileUseCase
from app.modules.profiles.domain.usecases.get_creator_profile import (
    GetCreatorProfileUseCase,
)


class FakeProfileRepo(CreatorProfileRepo):
    def __init__(self, profiles: Optional[list[CreatorProfile]] = None) -> None:
        self.items: dict[str, CreatorProfile] = {
            p.user_id: p for p in (profiles or [])
        }

    async def get_by_user_id(self, user_id):
        return self.items.get(user_id)

    async def upsert(self, profile):
        self.items[profile.user_id] = profile
        return profile


ALL_REQUIRED = {f: "x" for f in REQUIRED_PROFILE_FIELDS}


@pytest.mark.asyncio
async def test_get_my_profile_returns_blank_when_none():
    uc = GetMyProfileUseCase(profile_repo=FakeProfileRepo())
    out = await uc.execute(user_id="u_1")
    assert out.user_id == "u_1"
    assert out.is_complete is False


@pytest.mark.asyncio
async def test_upsert_creates_and_strips_fields():
    repo = FakeProfileRepo()
    uc = UpsertMyProfileUseCase(profile_repo=repo)
    fields = dict(ALL_REQUIRED, full_name="  Nguyen Van A  ")
    out = await uc.execute(user_id="u_1", fields=fields)
    assert out.full_name == "Nguyen Van A"
    assert out.is_complete is True
    assert repo.items["u_1"].full_name == "Nguyen Van A"


@pytest.mark.asyncio
async def test_upsert_replaces_existing():
    repo = FakeProfileRepo([CreatorProfile(user_id="u_1", full_name="Old")])
    uc = UpsertMyProfileUseCase(profile_repo=repo)
    out = await uc.execute(user_id="u_1", fields=dict(ALL_REQUIRED, full_name="New"))
    assert out.full_name == "New"


@pytest.mark.asyncio
async def test_admin_get_returns_none_when_missing():
    uc = GetCreatorProfileUseCase(profile_repo=FakeProfileRepo())
    assert await uc.execute(user_id="ghost") is None
