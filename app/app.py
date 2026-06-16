# app/app.py
"""Main FastAPI application setup."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import mongo_connection
from app.core.errors import register_exception_handlers
from app.core.settings import settings
from app.middlewares import setup_middleware
from app.modules.admin.presentation.routes import router as admin_router
from app.modules.auth.presentation.routes import router as auth_router
from app.modules.notifications.data.repo import NotificationDataRepository
from app.modules.notifications.presentation.routes import router as notifications_router
from app.jobs.migrate_qc_products import migrate_qc_products
from app.modules.users.data.model import UserRole
from app.modules.users.data.repo import UserDataRepository
from app.modules.users.domain.usecases.bootstrap_default_accounts import (
    BootstrapDefaultAccountsUseCase,
    DefaultAccount,
)
from app.modules.users.domain.usecases.create_user import CreateUserUseCase
from app.modules.users.presentation.routes import router as users_router
from app.modules.workspaces.data.model import Product
from app.modules.workspaces.data.repo import (
    ArticleDataRepository,
    ArticleEventDataRepository,
    FeedbackDataRepository,
    WorkspaceDataRepository,
)
from app.modules.workspaces.presentation.review_routes import router as review_router
from app.modules.workspaces.presentation.routes import router as workspaces_router
from app.modules.statistics.data.repo import StatisticsDataRepository
from app.modules.statistics.presentation.routes import router as statistics_router
from app.modules.interim_keys.data.repo import InterimKeyDataRepository
from app.modules.interim_keys.presentation.routes import router as interim_keys_router
from app.modules.chat.data.repo import ChatSessionDataRepository
from app.modules.chat.presentation.routes import router as chat_router
from app.modules.review_jobs.data.repo import ReviewJobDataRepository
from app.modules.review_jobs.presentation.routes import router as review_jobs_router
from app.modules.profiles.data.repo import CreatorProfileDataRepository
from app.modules.profiles.presentation.routes import router as profiles_router
from app.modules.reports.data.repo import AcceptanceReportDataRepository
from app.modules.reports.presentation.routes import router as reports_router
from app.modules.report_rule_jobs.data.repo import RuleJobDataRepository
from app.modules.report_rule_jobs.presentation.routes import router as report_rule_jobs_router


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo_connection.connect()

    # Ensure workspaces indexes
    await WorkspaceDataRepository().ensure_indexes()
    await ArticleDataRepository().ensure_indexes()
    await FeedbackDataRepository().ensure_indexes()
    await ArticleEventDataRepository().ensure_indexes()
    await NotificationDataRepository().ensure_indexes()
    await StatisticsDataRepository().ensure_indexes()
    await InterimKeyDataRepository().ensure_indexes()
    await ChatSessionDataRepository().ensure_indexes()
    await ReviewJobDataRepository().ensure_indexes()
    await CreatorProfileDataRepository().ensure_indexes()
    await AcceptanceReportDataRepository().ensure_indexes()
    await RuleJobDataRepository().ensure_indexes()

    # Heal legacy user docs (singular `qc_product` -> `qc_products` array) BEFORE
    # bootstrap reads any account. Idempotent; a no-op once migrated.
    migrated = await migrate_qc_products(await mongo_connection.get_db())
    if migrated:
        logging.getLogger("app.startup").info(
            f"qc_products migration healed {migrated} legacy user doc(s)"
        )

    # Bootstrap default accounts
    user_repo = UserDataRepository()
    bootstrap = BootstrapDefaultAccountsUseCase(
        user_repo=user_repo,
        uc_create_user=CreateUserUseCase(user_repo=user_repo),
    )

    creator_emails = [
        e.strip() for e in (settings.creator_emails or "").split(",") if e.strip()
    ]
    creator_passwords = [
        p.strip() for p in (settings.creator_passwords or "").split(",") if p.strip()
    ]
    if len(creator_emails) != len(creator_passwords):
        raise ValueError(
            f"CREATOR_EMAILS ({len(creator_emails)}) and CREATOR_PASSWORDS "
            f"({len(creator_passwords)}) must have the same number of entries"
        )
    creator_accounts = [
        DefaultAccount(email=email, password=password, role=UserRole.CREATOR)
        for email, password in zip(creator_emails, creator_passwords)
    ]

    await bootstrap.execute(
        [
            DefaultAccount(
                email=settings.superuser_email,
                password=settings.superuser_password,
                role=UserRole.SUPERUSER,
            ),
            DefaultAccount(
                email=settings.admin_email,
                password=settings.admin_password,
                role=UserRole.ADMIN,
            ),
            *creator_accounts,
            DefaultAccount(
                email=settings.qc_email,
                password=settings.qc_password,
                role=UserRole.QC,
                # Default QC account covers every product. Reconciled on every
                # startup by BootstrapDefaultAccountsUseCase.
                qc_products=list(Product),
            ),
        ]
    )

    yield


app = FastAPI(
    title="UGC Backend",
    description="UGC Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

setup_middleware(app)
register_exception_handlers(app)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(workspaces_router, prefix="/api/v1")
app.include_router(review_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(statistics_router, prefix="/api/v1")
app.include_router(interim_keys_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(review_jobs_router, prefix="/api/v1")
app.include_router(profiles_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(report_rule_jobs_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
