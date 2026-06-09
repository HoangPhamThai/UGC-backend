from datetime import datetime

from pydantic import BaseModel, Field


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., description="Label for the API key")


class CreateApiKeyResponse(BaseModel):
    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="Label")
    api_key: str = Field(..., description="Raw API key (shown only once)")
    key_prefix: str = Field(..., description="First 8 chars for identification")
    created_at: datetime = Field(..., description="Creation time")


class ApiKeyInfo(BaseModel):
    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="Label")
    key_prefix: str = Field(..., description="First 8 chars for identification")
    created_at: datetime = Field(..., description="Creation time")
