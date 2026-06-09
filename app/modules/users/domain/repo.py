from abc import ABC, abstractmethod
from typing import Optional

from app.modules.users.data.model import User


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
