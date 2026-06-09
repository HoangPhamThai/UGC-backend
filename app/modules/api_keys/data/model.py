from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class ApiKey(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("ak"), alias="_id")
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="User-given label")
    key_hash: str = Field(..., description="SHA-256 hash of the raw API key")
    key_prefix: str = Field(..., description="First 8 chars for identification")

    class Config:
        collection_name = "api_keys"
