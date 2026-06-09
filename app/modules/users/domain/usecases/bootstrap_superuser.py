import traceback
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import UserRole
from app.modules.users.domain.repo import UserRepo
from app.modules.users.domain.usecases.create_user import CreateUserUseCase


@dataclass(frozen=True)
class BootstrapSuperuserUseCase(LoggerMixin):
    user_repo: UserRepo
    uc_create_user: CreateUserUseCase

    async def execute(
        self, *, email: Optional[str], password: Optional[str]
    ) -> None:
        try:
            if await self.user_repo.exists_with_role(UserRole.SUPERUSER):
                self.log_info("Superuser already exists; bootstrap skipped")
                return

            if not email or not password:
                self.log_warning(
                    "No superuser exists and SUPERUSER_EMAIL/SUPERUSER_PASSWORD "
                    "not set; skipping bootstrap"
                )
                return

            existing = await self.user_repo.get_by_email(email)
            if existing is not None:
                self.log_error(
                    f"Cannot bootstrap superuser: email '{email}' is already "
                    f"registered with role={existing.role.value}"
                )
                return

            await self.uc_create_user.execute(
                email=email, password=password, role=UserRole.SUPERUSER
            )
            self.log_info(f"Superuser bootstrapped: {email}")
        except Exception as e:
            self.log_exception(f"BootstrapSuperuserUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
