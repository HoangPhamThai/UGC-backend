# app/core/errors.py
"""Global exception handlers that reshape every error response to the
frontend's standard {success: false, message: ...} envelope."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.modules.workspaces.domain.errors import (
    ArticleNotFoundError,
    ArticleStateConflictError,
    ClaimConflictError,
    FeedbackNotFoundError,
    FeedbackStateConflictError,
    InvalidInputError,
    QcMisconfiguredError,
    WorkspaceError,
    WorkspaceNameTakenError,
    WorkspaceNotFoundError,
)
from app.modules.statistics.domain.errors import CreatorNotFoundError, QcNotFoundError, StatisticsError
from app.modules.chat.domain.errors import ChatError, ChatSessionNotFoundError


def _envelope(message: str) -> dict:
    return {"success": False, "message": message}


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, content=_envelope(message))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        message = first.get("msg", "Invalid request")
        if loc:
            message = f"{loc}: {message}"
    else:
        message = "Invalid request"
    return JSONResponse(status_code=422, content=_envelope(message))


_DOMAIN_STATUS: dict[type[WorkspaceError], int] = {
    WorkspaceNotFoundError: 404,
    ArticleNotFoundError: 404,
    WorkspaceNameTakenError: 409,
    ArticleStateConflictError: 409,
    InvalidInputError: 400,
    QcMisconfiguredError: 500,
    ClaimConflictError: 409,
    FeedbackNotFoundError: 404,
    FeedbackStateConflictError: 409,
}


async def domain_exception_handler(request: Request, exc: WorkspaceError):
    status_code = _DOMAIN_STATUS.get(type(exc), 500)
    message = str(exc) if str(exc) else "Internal error"
    return JSONResponse(status_code=status_code, content=_envelope(message))


_STATISTICS_STATUS: dict[type[StatisticsError], int] = {
    CreatorNotFoundError: 404,
    QcNotFoundError: 404,
}


async def statistics_exception_handler(request: Request, exc: StatisticsError):
    status_code = _STATISTICS_STATUS.get(type(exc), 500)
    message = str(exc) if str(exc) else "Internal error"
    return JSONResponse(status_code=status_code, content=_envelope(message))


_CHAT_STATUS: dict[type[ChatError], int] = {
    ChatSessionNotFoundError: 404,
}


async def chat_exception_handler(request: Request, exc: ChatError):
    status_code = _CHAT_STATUS.get(type(exc), 500)
    message = str(exc) if str(exc) else "Internal error"
    return JSONResponse(status_code=status_code, content=_envelope(message))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    for exc_cls in _DOMAIN_STATUS:
        app.add_exception_handler(exc_cls, domain_exception_handler)
    for exc_cls in _STATISTICS_STATUS:
        app.add_exception_handler(exc_cls, statistics_exception_handler)
    for exc_cls in _CHAT_STATUS:
        app.add_exception_handler(exc_cls, chat_exception_handler)
