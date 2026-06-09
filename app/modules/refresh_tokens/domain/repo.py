from abc import ABC, abstractmethod
from typing import Optional

from app.modules.refresh_tokens.data.model import RefreshToken


class RefreshTokenRepo(ABC):

    @abstractmethod
    async def create(self, token: RefreshToken) -> RefreshToken:
        pass

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        pass

    @abstractmethod
    async def delete_all_by_user_id(self, user_id: str) -> int:
        """Delete all refresh tokens for a user. Returns count deleted."""
        pass
