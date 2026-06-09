from abc import ABC, abstractmethod
from typing import Optional

from app.modules.api_keys.data.model import ApiKey


class ApiKeyRepo(ABC):

    @abstractmethod
    async def create(self, api_key: ApiKey) -> ApiKey:
        pass

    @abstractmethod
    async def get_by_key_hash(self, key_hash: str) -> Optional[ApiKey]:
        pass

    @abstractmethod
    async def list_by_user_id(self, user_id: str) -> list[ApiKey]:
        pass

    @abstractmethod
    async def delete(self, key_id: str) -> bool:
        pass
