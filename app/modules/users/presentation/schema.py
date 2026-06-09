# app/modules/users/presentation/schema.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.core.permissions import Permission
from app.modules.users.data.model import UserRole
from app.modules.workspaces.data.model import Product


class UserMeResponse(BaseModel):
    id: str
    email: str
    is_active: bool
    role: UserRole
    qc_product: Optional[Product] = None
    permissions: list[Permission]
    created_at: datetime
