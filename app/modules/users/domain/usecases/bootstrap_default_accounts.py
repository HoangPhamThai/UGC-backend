import traceback
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import UserRole
from app.modules.users.domain.repo import UserRepo
from app.modules.users.domain.usecases.create_user import CreateUserUseCase
from app.modules.workspaces.data.model import Product


@dataclass(frozen=True)
class DefaultAccount:
    """A single default account to bootstrap on startup."""

    email: Optional[str]
    password: Optional[str]
    role: UserRole
    qc_products: Optional[list[Product]] = None


@dataclass(frozen=True)
class BootstrapDefaultAccountsUseCase(LoggerMixin):
    user_repo: UserRepo
    uc_create_user: CreateUserUseCase

    async def execute(self, accounts: list[DefaultAccount]) -> None:
        for account in accounts:
            await self._bootstrap_one(account)

    async def _bootstrap_one(self, account: DefaultAccount) -> None:
        role = account.role
        try:
            if not account.email or not account.password:
                self.log_warning(
                    f"Default {role.value} account not configured "
                    f"(email/password missing); skipping bootstrap"
                )
                return

            # Never bootstrap a second superuser if one already exists,
            # regardless of the configured email.
            if role == UserRole.SUPERUSER and await self.user_repo.exists_with_role(
                UserRole.SUPERUSER
            ):
                self.log_info("Superuser already exists; bootstrap skipped")
                return

            existing = await self.user_repo.get_by_email(account.email)
            if existing is not None:
                self.log_info(
                    f"Default {role.value} account already exists: "
                    f"'{account.email}' (role={existing.role.value}); "
                    f"bootstrap skipped"
                )
                return

            await self.uc_create_user.execute(
                email=account.email,
                password=account.password,
                role=role,
                qc_products=account.qc_products,
            )
            self.log_info(
                f"Default {role.value} account bootstrapped: {account.email}"
            )
        except Exception as e:
            self.log_exception(
                f"BootstrapDefaultAccountsUseCase error for {role.value} "
                f"account: {str(e)}"
            )
            self.log_exception(traceback.format_exc())
