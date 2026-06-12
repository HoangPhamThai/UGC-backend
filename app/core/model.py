import uuid
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar, Optional, Dict, List, Literal


T = TypeVar("T")


def make_prefixed_id(prefix: str) -> str:
    """Generate a prefixed ID like 'kb_<uuid hex>'."""
    return f"{prefix}_{uuid.uuid4().hex}"


def to_epoch_ms(dt: datetime) -> int:
    """Milliseconds since the Unix epoch.

    Treats a naive datetime as UTC. MongoDB returns naive datetimes (the driver
    is not tz_aware here) holding the UTC wall-clock; calling ``dt.timestamp()``
    directly would interpret them as the server's LOCAL time and skew the result
    by the server's UTC offset. Normalizing naive -> UTC makes the output correct
    regardless of the server timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


# --- Base model ---


class BaseMongoModel(BaseModel):
    """Reusable base class for MongoDB documents keyed by prefixed string ID."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # --- Pydantic v2 config ---
    model_config = ConfigDict(
        populate_by_name=True,  # accept both "id" and "_id"
        ser_json_timedelta="iso8601",
    )


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class StandardResponse(BaseModel, Generic[T]):
    """
    Standard success response wrapper for all API endpoints.

    Format:
    {
        "success": true,
        "data": <actual_response_data>,
        "message": "Optional success message"
    }
    """

    success: bool = Field(True, description="Indicates if the request was successful")
    data: Optional[T] = Field(None, description="The actual response data")
    message: Optional[str] = Field(None, description="Optional success message")


class ErrorResponse(BaseModel):
    """
    Standard error response format.

    Format:
    {
        "success": false,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Human-readable error message",
            "details": {
                "field": "email",
                "reason": "Invalid email format"
            }
        }
    }
    """

    success: bool = Field(False, description="Indicates if the request was successful")
    error: ErrorDetail = Field(..., description="Error information")


def create_success_response(
    data: Optional[T] = None, message: Optional[str] = None
) -> StandardResponse[T]:
    """Create a standard success response."""
    return StandardResponse(success=True, data=data, message=message)


def create_error_response(
    code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """Create a standard error response."""
    error_detail = ErrorDetail(code=code, message=message, details=details)
    return ErrorResponse(success=False, error=error_detail)
