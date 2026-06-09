import traceback
from dataclasses import dataclass

from jwt import PyJWTError

from app.core.logging_mixin import LoggerMixin
from app.core.security import create_access_token, decode_token, hash_refresh_token
from app.modules.refresh_tokens.domain.repo import RefreshTokenRepo


@dataclass(frozen=True)
class RefreshTokenUseCase(LoggerMixin):
    refresh_token_repo: RefreshTokenRepo

    async def execute(self, *, refresh_token: str) -> str:
        """Validate refresh token and return a new access token."""
        try:
            try:
                payload = decode_token(refresh_token)
            except PyJWTError:
                raise ValueError("Invalid or expired refresh token")

            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")

            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("Invalid token payload")

            token_hash = hash_refresh_token(refresh_token)
            token_record = await self.refresh_token_repo.get_by_token_hash(token_hash)
            if token_record is None:
                raise ValueError("Refresh token has been revoked")

            return create_access_token(user_id)
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"RefreshTokenUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to refresh token: {str(e)}") from e
