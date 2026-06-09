from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class User(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("u"), alias="_id")
    email: str = Field(..., description="Unique email")
    password_hashed: str = Field(..., description="Bcrypt hashed password")
    is_active: bool = Field(default=True, description="Whether user can authenticate")

    class Config:
        collection_name = "users"
