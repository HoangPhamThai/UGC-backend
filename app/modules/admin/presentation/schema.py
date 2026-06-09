from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app.modules.users.data.model import UserRole


# --- Requests ---


class CreateManagedUserRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    role: Literal[UserRole.ADMIN, UserRole.QC] = Field(
        ..., description="Role to assign; only 'admin' or 'qc' are accepted"
    )


class UpdateManagedUserRequest(BaseModel):
    is_active: Optional[bool] = Field(
        default=None, description="Set false to soft-deactivate"
    )
    password: Optional[str] = Field(
        default=None, min_length=8, description="New password"
    )


# --- Responses ---


class ManagedUserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="Account creation time")


class ManagedUserListResponse(BaseModel):
    items: list[ManagedUserResponse]
    total: int = Field(..., description="Total users matching the role filter")
    page: int = Field(..., description="1-indexed page number")
    page_size: int = Field(..., description="Items per page")
