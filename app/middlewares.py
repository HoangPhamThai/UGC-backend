"""
Middleware configuration for the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.core.rate_limit import limiter


def setup_middleware(app: FastAPI):
    """Setup all middleware for the FastAPI application."""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Gzip compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Rate limiting (slowapi)
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
