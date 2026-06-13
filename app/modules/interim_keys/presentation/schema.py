# app/modules/interim_keys/presentation/schema.py
from pydantic import BaseModel


class InterimKeyResponse(BaseModel):
    interim_key: str
    expires_at: int  # epoch ms
