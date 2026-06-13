# app/modules/chat/data/model.py
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.core.model import BaseMongoModel, make_prefixed_id


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("cm"))
    role: ChatRole
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatSession(BaseMongoModel):
    id: str = Field(default_factory=lambda: make_prefixed_id("cs"), alias="_id")
    user_id: str
    title: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)

    class Config:
        collection_name = "chat_sessions"
