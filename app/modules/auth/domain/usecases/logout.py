import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.refresh_tokens.domain.repo import RefreshTokenRepo


@dataclass(frozen=True)
class LogoutUseCase(LoggerMixin):
    refresh_token_repo: RefreshTokenRepo

    async def execute(self, *, user_id: str) -> None:
        """Revoke all refresh tokens for the user (logout everywhere)."""
        try:
            count = await self.refresh_token_repo.delete_all_by_user_id(user_id)
            self.log_info(f"Logged out user {user_id}, revoked {count} token(s)")
        except Exception as e:
            self.log_exception(f"LogoutUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to logout: {str(e)}") from e
