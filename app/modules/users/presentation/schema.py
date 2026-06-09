from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.users.data.model import UserRole


class UserMeResponse(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email")
    is_active: bool = Field(..., description="Whether user is active")
    role: UserRole = Field(..., description="User role")
    created_at: datetime = Field(..., description="Account creation time")
