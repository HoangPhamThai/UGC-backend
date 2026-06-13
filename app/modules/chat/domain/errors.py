# app/modules/chat/domain/errors.py
class ChatError(Exception):
    """Base class for chat domain errors."""


class ChatSessionNotFoundError(ChatError):
    """Session does not exist or is not owned by the caller. Maps to 404."""

    def __init__(self, message: str = "Chat session not found") -> None:
        super().__init__(message)
