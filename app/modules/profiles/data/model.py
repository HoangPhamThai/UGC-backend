# app/modules/profiles/data/model.py
from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id

# Fields required for the profile to count as "complete" (spec §3.3).
# `current_address` is intentionally excluded — it falls back to primary_address.
REQUIRED_PROFILE_FIELDS: tuple[str, ...] = (
    "full_name",
    "date_of_birth",
    "social_id",
    "social_id_date_of_issue",
    "social_id_place_of_issue",
    "primary_address",
    "tax_number",
    "bank_account_number",
    "bank_name",
    "bank_branch",
)


class CreatorProfile(BaseMongoModel):
    """Self-service personal + banking data for a creator (spec §3.3).

    Dates are stored as plain strings (e.g. "1990-01-15") — these are
    display-only contract fields, so we avoid the bson date encoding caveat
    that Article.on_air_date has to deal with.
    """

    id: str = Field(default_factory=lambda: make_prefixed_id("cp"), alias="_id")
    user_id: str = Field(..., description="Owning creator user id (unique)")

    full_name: str = Field(default="")
    date_of_birth: str = Field(default="")
    social_id: str = Field(default="")
    social_id_date_of_issue: str = Field(default="")
    social_id_place_of_issue: str = Field(default="")
    primary_address: str = Field(default="")
    current_address: str = Field(default="", description="Optional; falls back to primary_address")
    tax_number: str = Field(default="")
    bank_account_number: str = Field(default="")
    bank_name: str = Field(default="")
    bank_branch: str = Field(default="")

    @property
    def is_complete(self) -> bool:
        return all(str(getattr(self, f)).strip() for f in REQUIRED_PROFILE_FIELDS)

    class Config:
        collection_name = "creator_profiles"
