# app/modules/interim_keys/domain/repo.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from app.modules.interim_keys.data.model import InterimKey


class InterimKeyRepo(ABC):
    @abstractmethod
    async def create(self, key: InterimKey) -> InterimKey: ...

    @abstractmethod
    async def get_active_by_hash(
        self, key_hash: str, now: datetime
    ) -> Optional[InterimKey]:
        """Return the key with this hash only if it has not expired (expires_at > now)."""
        ...

    @abstractmethod
    async def delete_by_hash(self, key_hash: str) -> bool:
        """Delete the key; return True if a record was removed, False otherwise."""
        ...
