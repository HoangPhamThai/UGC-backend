# app/modules/interim_keys/domain/usecases/issue_interim_key.py
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.logging_mixin import LoggerMixin
from app.core.security import hash_interim_key
from app.modules.interim_keys.data.model import InterimKey
from app.modules.interim_keys.domain.repo import InterimKeyRepo

INTERIM_KEY_TTL_MINUTES = 10


@dataclass(frozen=True)
class IssuedInterimKey:
    raw_key: str
    expires_at: datetime


@dataclass(frozen=True)
class IssueInterimKeyUseCase(LoggerMixin):
    repo: InterimKeyRepo

    async def execute(self, *, user_id: str, now: datetime) -> IssuedInterimKey:
        raw_key = secrets.token_urlsafe(32)
        expires_at = now + timedelta(minutes=INTERIM_KEY_TTL_MINUTES)
        await self.repo.create(
            InterimKey(
                user_id=user_id,
                key_hash=hash_interim_key(raw_key),
                expires_at=expires_at,
            )
        )
        self.log_info(f"Interim key issued for user={user_id}")
        return IssuedInterimKey(raw_key=raw_key, expires_at=expires_at)
