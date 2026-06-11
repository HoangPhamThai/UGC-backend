# app/modules/users/data/model.py
from enum import Enum

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
    qc_products: list[Product] = Field(
        default_factory=list,
        description=(
            "Products the QC is assigned to; must be a non-empty set iff "
            "role=qc, must be empty otherwise. A QC may cover several products."
        ),
    )

    @model_validator(mode="after")
    def _check_qc_products(self) -> "User":
        if self.role == UserRole.QC and not self.qc_products:
            raise ValueError("qc_products is required (non-empty) when role=qc")
        if self.role != UserRole.QC and self.qc_products:
            raise ValueError("qc_products must be empty when role is not qc")
        # De-duplicate while keeping the canonical product display order.
        if self.qc_products:
            order = list(Product)
            unique = sorted(set(self.qc_products), key=order.index)
            object.__setattr__(self, "qc_products", unique)
        return self

    class Config:
        collection_name = "users"
