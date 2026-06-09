# app/modules/users/data/model.py
from enum import Enum
from typing import Optional

from pydantic import Field, model_validator

from app.core.model import BaseMongoModel, make_prefixed_id
from app.modules.workspaces.data.model import Product


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
    qc_product: Optional[Product] = Field(
        default=None,
        description="Product the QC is assigned to; required iff role=qc, must be None otherwise",
    )

    @model_validator(mode="after")
    def _check_qc_product(self) -> "User":
        if self.role == UserRole.QC and self.qc_product is None:
            raise ValueError("qc_product is required when role=qc")
        if self.role != UserRole.QC and self.qc_product is not None:
            raise ValueError("qc_product must be None when role is not qc")
        return self

    class Config:
        collection_name = "users"
