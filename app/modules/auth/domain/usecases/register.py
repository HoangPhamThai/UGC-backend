import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.domain.usecases.create_user import CreateUserUseCase


@dataclass(frozen=True)
class RegisterUseCase(LoggerMixin):
    uc_create_user: CreateUserUseCase

    async def execute(self, *, email: str, password: str) -> None:
        try:
            await self.uc_create_user.execute(email=email, password=password)
            self.log_info(f"User registered: {email}")
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"RegisterUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to register: {str(e)}") from e
