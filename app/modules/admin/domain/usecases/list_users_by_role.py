import traceback
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.users.domain.repo import UserRepo


@dataclass(frozen=True)
class ListUsersByRoleResult:
    items: list[User]
    total: int


@dataclass(frozen=True)
class ListUsersByRoleUseCase(LoggerMixin):
    user_repo: UserRepo

    async def execute(
        self, *, role: UserRole, page: int, page_size: int
    ) -> ListUsersByRoleResult:
        try:
            if page < 1:
                raise ValueError("page must be >= 1")
            if page_size < 1 or page_size > 200:
                raise ValueError("page_size must be between 1 and 200")

            skip = (page - 1) * page_size
            items = await self.user_repo.list_by_role(
                role, skip=skip, limit=page_size
            )
            total = await self.user_repo.count_by_role(role)
            return ListUsersByRoleResult(items=items, total=total)
        except ValueError:
            raise
        except Exception as e:
            self.log_exception(f"ListUsersByRoleUseCase error: {str(e)}")
            self.log_exception(traceback.format_exc())
            raise Exception(f"Failed to list users: {str(e)}") from e
