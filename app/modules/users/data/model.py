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

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_qc_product(cls, data):
        """Back-compat: legacy user docs stored a singular scalar `qc_product`
        instead of the `qc_products` array. Normalize on read so old documents
        load cleanly (mirrors the migrate_qc_products job). The stray field is
        always dropped; it only seeds `qc_products` for QC users that don't
        already have one."""
        if not isinstance(data, dict) or "qc_product" not in data:
            return data
        data = dict(data)
        legacy = data.pop("qc_product")
        if data.get("role") == UserRole.QC and legacy and not data.get("qc_products"):
            data["qc_products"] = [legacy]
        return data

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
