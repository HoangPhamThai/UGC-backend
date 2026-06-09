import traceback
from dataclasses import dataclass
from typing import Optional

from app.core.logging_mixin import LoggerMixin
from app.core.security import hash_password
from app.modules.users.data.model import User
from app.modules.users.domain.repo import UserRepo


@dataclass(frozen=True)
class UpdateManagedUserUseCase(LoggerMixin):
    user_repo: UserRepo

    async def execute(
        self,
        *,
        user_id: str,
        is_active: Optional[bool],
        password: Optional[str],
    ) -> Optional[User]:
        try:
            user = await self.user_repo.get_by_id(user_id)
            if user is None:
                return None

            if is_active is not None:
                user.is_active = is_active
            if password is not None:
                user.password_hashed = hash_password(password)

            updated = await self.user_repo.update(user)
            self.log_info(f"User updated: id={updated.id}")
            return updated
        except Exception as e:
            self.log_exception(f"UpdateManagedUserUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to update user: {str(e)}") from e
