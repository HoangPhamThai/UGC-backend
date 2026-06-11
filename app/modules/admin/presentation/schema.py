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
    qc_products: Optional[list[Product]] = Field(
        default=None,
        description=(
            "Products to assign the QC to (one or more). Required (non-empty) "
            "when role=qc, must be omitted/empty otherwise"
        ),
    )


class UpdateManagedUserRequest(BaseModel):
    is_active: Optional[bool] = Field(
        default=None, description="Set false to soft-deactivate"
    )
    password: Optional[str] = Field(
        default=None, min_length=8, description="New password"
    )
    qc_products: Optional[list[Product]] = Field(
        default=None,
        description=(
            "Reassign the QC's products (one or more; replaces the existing "
            "set). Only valid for QC users; must be non-empty when provided"
        ),
    )


# --- Responses ---


class ManagedUserResponse(BaseModel):
    id: str
    email: str
    role: UserRole
    qc_products: list[Product] = Field(default_factory=list)
    is_active: bool
    created_at: datetime


class ManagedUserListResponse(BaseModel):
    items: list[ManagedUserResponse]
    total: int
    page: int
    page_size: int
