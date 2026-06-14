from pydantic import BaseModel, Field

from app.modules.profiles.data.model import CreatorProfile


class ProfileResponse(BaseModel):
    full_name: str
    date_of_birth: str
    social_id: str
    social_id_date_of_issue: str
    social_id_place_of_issue: str
    primary_address: str
    current_address: str
    tax_number: str
    bank_account_number: str
    bank_name: str
    bank_branch: str
    is_complete: bool

    @classmethod
    def from_model(cls, p: CreatorProfile) -> "ProfileResponse":
        return cls(
            full_name=p.full_name,
            date_of_birth=p.date_of_birth,
            social_id=p.social_id,
            social_id_date_of_issue=p.social_id_date_of_issue,
            social_id_place_of_issue=p.social_id_place_of_issue,
            primary_address=p.primary_address,
            current_address=p.current_address,
            tax_number=p.tax_number,
            bank_account_number=p.bank_account_number,
            bank_name=p.bank_name,
            bank_branch=p.bank_branch,
            is_complete=p.is_complete,
        )


class UpdateProfileRequest(BaseModel):
    """Full replace — the form always submits every field."""
    full_name: str = Field(default="")
    date_of_birth: str = Field(default="")
    social_id: str = Field(default="")
    social_id_date_of_issue: str = Field(default="")
    social_id_place_of_issue: str = Field(default="")
    primary_address: str = Field(default="")
    current_address: str = Field(default="")
    tax_number: str = Field(default="")
    bank_account_number: str = Field(default="")
    bank_name: str = Field(default="")
    bank_branch: str = Field(default="")
