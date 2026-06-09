"""
Main FastAPI application setup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
import logging
import sys

from app.core.db import mongo_connection
from app.core.settings import settings
from app.middlewares import setup_middleware
from app.modules.admin.presentation.routes import router as admin_router
from app.modules.auth.presentation.routes import router as auth_router
from app.modules.users.data.repo import UserDataRepository
from app.modules.users.domain.usecases.bootstrap_superuser import (
    BootstrapSuperuserUseCase,
)
from app.modules.users.domain.usecases.create_user import CreateUserUseCase
from app.modules.users.presentation.routes import router as users_router


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo_connection.connect()

    user_repo = UserDataRepository()
    bootstrap = BootstrapSuperuserUseCase(
        user_repo=user_repo,
        uc_create_user=CreateUserUseCase(user_repo=user_repo),
    )
    await bootstrap.execute(
        email=settings.superuser_email,
        password=settings.superuser_password,
    )

    yield


app = FastAPI(
    title="GreenRAG Backend",
    description="GreenRAG Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

setup_middleware(app)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
