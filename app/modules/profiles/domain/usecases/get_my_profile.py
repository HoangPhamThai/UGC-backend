from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.profiles.data.model import CreatorProfile
from app.modules.profiles.domain.repo import CreatorProfileRepo


@dataclass(frozen=True)
class GetMyProfileUseCase(LoggerMixin):
    profile_repo: CreatorProfileRepo

    async def execute(self, *, user_id: str) -> CreatorProfile:
        existing = await self.profile_repo.get_by_user_id(user_id)
        return existing or CreatorProfile(user_id=user_id)
