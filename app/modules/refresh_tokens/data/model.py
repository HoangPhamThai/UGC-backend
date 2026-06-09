from datetime import datetime

from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class RefreshToken(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("rt"), alias="_id")
    user_id: str = Field(..., description="Owner user ID")
    token_hash: str = Field(..., description="SHA-256 hash of the raw JWT")
    expires_at: datetime = Field(..., description="Token expiration time")

    class Config:
        collection_name = "refresh_tokens"
