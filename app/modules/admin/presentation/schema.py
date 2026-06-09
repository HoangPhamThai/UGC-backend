# app/modules/admin/presentation/schema.py
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app.modules.users.data.model import UserRole
from app.modules.workspaces.data.model import Product


# --- Requests ---


class CreateManagedUserRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    role: Literal[UserRole.ADMIN, UserRole.QC] = Field(
        ..., description="Role to assign; only 'admin' or 'qc' are accepted"
    )
    qc_product: Optional[Product] = Field(
        default=None,
        description="Required when role=qc, must be omitted/null otherwise",
    )


class UpdateManagedUserRequest(BaseModel):
    is_active: Optional[bool] = Field(
        default=None, description="Set false to soft-deactivate"
    )
    password: Optional[str] = Field(
        default=None, min_length=8, description="New password"
    )
    qc_product: Optional[Product] = Field(
        default=None,
        description="Reassign the QC to a different product (only valid for QC users)",
    )


# --- Responses ---


class ManagedUserResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    qc_product: Optional[Product] = None
    is_active: bool
    created_at: datetime


class ManagedUserListResponse(BaseModel):
    items: list[ManagedUserResponse]
    total: int
    page: int
    page_size: int
