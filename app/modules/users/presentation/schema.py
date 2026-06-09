from datetime import datetime

from pydantic import BaseModel, Field


class UserMeResponse(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="Account creation time")
