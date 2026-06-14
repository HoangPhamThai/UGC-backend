from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.profiles.data.model import CreatorProfile
from app.modules.profiles.domain.repo import CreatorProfileRepo

# The settable string fields (everything on the model except identity/timestamps).
_EDITABLE_FIELDS: tuple[str, ...] = (
    "full_name",
    "date_of_birth",
    "social_id",
    "social_id_date_of_issue",
    "social_id_place_of_issue",
    "primary_address",
    "current_address",
    "tax_number",
    "bank_account_number",
    "bank_name",
    "bank_branch",
)


@dataclass(frozen=True)
class UpsertMyProfileUseCase(LoggerMixin):
    profile_repo: CreatorProfileRepo

    async def execute(self, *, user_id: str, fields: dict) -> CreatorProfile:
        existing = await self.profile_repo.get_by_user_id(user_id)
        profile = existing or CreatorProfile(user_id=user_id)
        for key in _EDITABLE_FIELDS:
            if key in fields:
                setattr(profile, key, (fields[key] or "").strip())
        saved = await self.profile_repo.upsert(profile)
        self.log_info(f"Profile upserted: user_id={user_id} complete={saved.is_complete}")
        return saved
