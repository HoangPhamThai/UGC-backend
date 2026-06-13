# app/modules/interim_keys/domain/usecases/revoke_interim_key.py
from dataclasses import dataclass

from app.core.logging_mixin import LoggerMixin
from app.core.security import hash_interim_key
from app.modules.interim_keys.domain.repo import InterimKeyRepo


@dataclass(frozen=True)
class RevokeInterimKeyUseCase(LoggerMixin):
    repo: InterimKeyRepo

    async def execute(self, *, raw_key: str) -> bool:
        return await self.repo.delete_by_hash(hash_interim_key(raw_key))
