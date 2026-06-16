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
from app.modules.statistics.domain.errors import (
    ArticleNotFoundError as StatisticsArticleNotFoundError,
    CreatorNotFoundError,
    QcNotFoundError,
    StatisticsError,
)
from app.modules.chat.domain.errors import ChatError, ChatSessionNotFoundError
from app.modules.review_jobs.domain.errors import ReviewJobError, ReviewJobNotFoundError
from app.modules.report_rule_jobs.domain.errors import RuleJobError, RuleJobNotFoundError
from app.modules.reports.domain.errors import (
    ReportError,
    ReportNotFoundError,
    ReportStateConflictError,
    ReportValidationError,
)


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
    StatisticsArticleNotFoundError: 404,
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


_REVIEW_JOB_STATUS: dict[type[ReviewJobError], int] = {
    ReviewJobNotFoundError: 404,
}


async def review_jobs_exception_handler(request: Request, exc: ReviewJobError):
    status_code = _REVIEW_JOB_STATUS.get(type(exc), 500)
    message = str(exc) if str(exc) else "Internal error"
    return JSONResponse(status_code=status_code, content=_envelope(message))


_RULE_JOB_STATUS: dict[type[RuleJobError], int] = {
    RuleJobNotFoundError: 404,
}


async def rule_jobs_exception_handler(request: Request, exc: RuleJobError):
    status_code = _RULE_JOB_STATUS.get(type(exc), 500)
    message = str(exc) if str(exc) else "Internal error"
    return JSONResponse(status_code=status_code, content=_envelope(message))


_REPORTS_STATUS: dict[type[ReportError], int] = {
    ReportNotFoundError: 404,
    ReportStateConflictError: 409,
    ReportValidationError: 400,
}


async def reports_exception_handler(request: Request, exc: ReportError):
    status_code = _REPORTS_STATUS.get(type(exc), 500)
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
    for exc_cls in _REVIEW_JOB_STATUS:
        app.add_exception_handler(exc_cls, review_jobs_exception_handler)
    for exc_cls in _RULE_JOB_STATUS:
        app.add_exception_handler(exc_cls, rule_jobs_exception_handler)
    for exc_cls in _REPORTS_STATUS:
        app.add_exception_handler(exc_cls, reports_exception_handler)
