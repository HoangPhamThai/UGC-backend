import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.logging_mixin import LoggerMixin
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.core.settings import settings
from app.modules.refresh_tokens.data.model import RefreshToken
from app.modules.refresh_tokens.domain.repo import RefreshTokenRepo
from app.modules.users.domain.repo import UserRepo


@dataclass
class LoginResult:
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class LoginUseCase(LoggerMixin):
    user_repo: UserRepo
    refresh_token_repo: RefreshTokenRepo

    async def execute(self, *, email: str, password: str) -> LoginResult:
        try:
            user = await self.user_repo.get_by_email(email)
            if user is None:
                raise ValueError("Invalid credentials")

            if not user.is_active:
                raise ValueError("User account is inactive")

            if not verify_password(password, user.password_hashed):
                raise ValueError("Invalid credentials")

            access_token = create_access_token(user.id)
            raw_refresh_token = create_refresh_token(user.id)

            token_record = RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw_refresh_token),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.refresh_token_expire_days),
            )
            await self.refresh_token_repo.create(token_record)

            self.log_info(f"User logged in: id={user.id}")
            return LoginResult(
                access_token=access_token,
                refresh_token=raw_refresh_token,
            )
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"LoginUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to login: {str(e)}") from e
