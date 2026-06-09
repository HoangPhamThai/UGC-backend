"""
Main FastAPI application setup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
import logging
import sys

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.middlewares import setup_middleware
from app.modules.auth.presentation.routes import router as auth_router
from app.modules.users.presentation.routes import router as users_router
from app.modules.api_keys.presentation.routes import router as api_keys_router
from app.core.db import mongo_connection


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await mongo_connection.connect()
    yield
    # Shutdown (if needed in the future)


# Create FastAPI app
app = FastAPI(
    title="GreenRAG Backend",
    description="GreenRAG Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Setup middleware
setup_middleware(app)

# Convert slowapi's RateLimitExceeded into a clean 429 JSON response
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # type: ignore[arg-type]

# Register routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
