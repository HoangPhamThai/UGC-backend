# app/modules/chat/presentation/schema.py
from typing import Optional

from pydantic import BaseModel, Field

from app.core.model import to_epoch_ms
from app.modules.chat.data.model import ChatMessage, ChatRole, ChatSession
from app.modules.chat.domain.repo import ChatSessionSummary


class ChatMessageResponse(BaseModel):
    id: str
    role: ChatRole
    content: str
    created_at: int  # epoch ms

    @classmethod
    def from_message(cls, m: ChatMessage) -> "ChatMessageResponse":
        return cls(id=m.id, role=m.role, content=m.content, created_at=to_epoch_ms(m.created_at))


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: int
    updated_at: int
    messages: list[ChatMessageResponse]

    @classmethod
    def from_session(cls, s: ChatSession) -> "ChatSessionResponse":
        return cls(
            id=s.id,
            title=s.title,
            created_at=to_epoch_ms(s.created_at),
            updated_at=to_epoch_ms(s.updated_at),
            messages=[ChatMessageResponse.from_message(m) for m in s.messages],
        )


class ChatSessionSummaryResponse(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: int
    updated_at: int

    @classmethod
    def from_summary(cls, s: ChatSessionSummary) -> "ChatSessionSummaryResponse":
        return cls(
            id=s.id,
            title=s.title,
            message_count=s.message_count,
            created_at=to_epoch_ms(s.created_at),
            updated_at=to_epoch_ms(s.updated_at),
        )


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionSummaryResponse]
    total: int


class MessagesResponse(BaseModel):
    messages: list[ChatMessageResponse]


class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)


class MessageInput(BaseModel):
    role: ChatRole
    content: str = Field(..., min_length=1)


class AppendMessagesRequest(BaseModel):
    messages: list[MessageInput] = Field(..., min_length=1)
