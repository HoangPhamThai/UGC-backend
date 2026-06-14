from abc import ABC, abstractmethod
from typing import Optional

from app.modules.profiles.data.model import CreatorProfile


class CreatorProfileRepo(ABC):

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[CreatorProfile]:
        pass

    @abstractmethod
    async def upsert(self, profile: CreatorProfile) -> CreatorProfile:
        pass
