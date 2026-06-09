import traceback
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User
from app.modules.users.domain.repo import UserRepo


@dataclass(frozen=True)
class GetUserByIdUseCase(LoggerMixin):
    user_repo: UserRepo

    async def execute(self, *, user_id: str) -> Optional[User]:
        try:
            return await self.user_repo.get_by_id(user_id)
        except Exception as e:
            self.log_exception(f"GetUserByIdUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to get user: {str(e)}") from e
