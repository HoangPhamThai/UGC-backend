# app/modules/users/presentation/schema.py
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.permissions import Permission
from app.modules.users.data.model import UserRole
from app.modules.workspaces.data.model import Product


class UserMeResponse(BaseModel):
    id: str
    email: str
    is_active: bool
    role: UserRole
    qc_products: list[Product] = Field(default_factory=list)
    permissions: list[Permission]
    created_at: datetime
