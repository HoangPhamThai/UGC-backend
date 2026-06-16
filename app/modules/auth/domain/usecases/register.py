import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.core.settings import settings
from app.modules.users.data.model import UserRole
from app.modules.users.domain.usecases.create_user import CreateUserUseCase
from app.modules.workspaces.data.model import Product


class RoleNotAllowedError(Exception):
    """Raised when a requested registration role is not permitted (superuser, or
    a non-creator role while DEMO_MODE is off). The route maps this to HTTP 403."""


@dataclass(frozen=True)
class RegisterUseCase(LoggerMixin):
    uc_create_user: CreateUserUseCase

    async def execute(
        self, *, email: str, password: str, role: UserRole = UserRole.CREATOR
    ) -> None:
        try:
            if role == UserRole.SUPERUSER:
                raise RoleNotAllowedError("Cannot self-register as superuser")
            if role != UserRole.CREATOR and not settings.demo_mode:
                raise RoleNotAllowedError(
                    "Only creator registration is allowed"
                )

            qc_products = list(Product) if role == UserRole.QC else None
            await self.uc_create_user.execute(
                email=email, password=password, role=role, qc_products=qc_products
            )
            self.log_info(f"User registered: {email} role={role.value}")
        except (ValueError, RoleNotAllowedError):
            raise
        except Exception as e:
            self.log_exception(f"RegisterUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to register: {str(e)}") from e
