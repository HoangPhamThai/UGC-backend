import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.core.security import hash_password
from app.modules.users.data.model import User
from app.modules.users.domain.repo import UserRepo


@dataclass(frozen=True)
class CreateUserUseCase(LoggerMixin):
    user_repo: UserRepo

    async def execute(self, *, email: str, password: str) -> User:
        try:
            existing = await self.user_repo.get_by_email(email)
            if existing is not None:
                raise ValueError(f"Email already registered: {email}")

            user = User(
                email=email,
                password_hashed=hash_password(password),
            )
            created = await self.user_repo.create(user)
            self.log_info(f"User created: id={created.id}")
            return created
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"CreateUserUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to create user: {str(e)}") from e
