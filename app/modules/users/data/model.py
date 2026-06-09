from enum import Enum

from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class UserRole(str, Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    QC = "qc"
    CREATOR = "creator"


class User(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("u"), alias="_id")
    email: str = Field(..., description="Unique email")
    password_hashed: str = Field(..., description="Bcrypt hashed password")
    is_active: bool = Field(default=True, description="Whether user can authenticate")
    role: UserRole = Field(default=UserRole.CREATOR, description="User role")

    class Config:
        collection_name = "users"
