# app/modules/interim_keys/data/model.py
from datetime import datetime

from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class InterimKey(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("ik"), alias="_id")
    user_id: str
    key_hash: str = Field(..., description="sha256 of the raw interim key")
    expires_at: datetime = Field(..., description="UTC; issued_at + TTL")

    class Config:
        collection_name = "interim_keys"
