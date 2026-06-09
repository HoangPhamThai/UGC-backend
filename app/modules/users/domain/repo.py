from abc import ABC, abstractmethod
from typing import Optional

from app.modules.users.data.model import User, UserRole


class UserRepo(ABC):

    @abstractmethod
    async def create(self, user: User) -> User:
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        pass

    @abstractmethod
    async def exists_with_role(self, role: UserRole) -> bool:
        pass

    @abstractmethod
    async def list_by_role(
        self, role: UserRole, *, skip: int = 0, limit: int = 50
    ) -> list[User]:
        pass

    @abstractmethod
    async def count_by_role(self, role: UserRole) -> int:
        pass
