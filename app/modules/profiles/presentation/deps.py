from functools import lru_cache

from app.modules.profiles.data.repo import CreatorProfileDataRepository
from app.modules.profiles.domain.repo import CreatorProfileRepo
from app.modules.profiles.domain.usecases.get_creator_profile import (
    GetCreatorProfileUseCase,
)
from app.modules.profiles.domain.usecases.get_my_profile import GetMyProfileUseCase
from app.modules.profiles.domain.usecases.upsert_my_profile import UpsertMyProfileUseCase


@lru_cache(maxsize=1)
def get_profile_repo() -> CreatorProfileRepo:
    return CreatorProfileDataRepository()


def get_uc_get_my_profile() -> GetMyProfileUseCase:
    return GetMyProfileUseCase(profile_repo=get_profile_repo())


def get_uc_upsert_my_profile() -> UpsertMyProfileUseCase:
    return UpsertMyProfileUseCase(profile_repo=get_profile_repo())


def get_uc_get_creator_profile() -> GetCreatorProfileUseCase:
    return GetCreatorProfileUseCase(profile_repo=get_profile_repo())
