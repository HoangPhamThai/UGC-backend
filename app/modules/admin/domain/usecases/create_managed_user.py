import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.users.domain.usecases.create_user import CreateUserUseCase


@dataclass(frozen=True)
class CreateManagedUserUseCase(LoggerMixin):
    uc_create_user: CreateUserUseCase

    async def execute(
        self, *, email: str, password: str, role: UserRole
    ) -> User:
        try:
            if role not in (UserRole.ADMIN, UserRole.QC):
                raise ValueError(
                    f"Cannot create user with role '{role.value}' via this endpoint"
                )
            return await self.uc_create_user.execute(
                email=email, password=password, role=role
            )
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"CreateManagedUserUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to create user: {str(e)}") from e
