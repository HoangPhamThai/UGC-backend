from pydantic import BaseModel, Field, EmailStr

from app.modules.users.data.model import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    role: UserRole = Field(
        default=UserRole.CREATOR,
        description="Requested role; non-creator roles require DEMO_MODE",
    )


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="JWT refresh token")


class AccessTokenResponse(BaseModel):
    access_token: str = Field(..., description="New JWT access token")
