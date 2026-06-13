from datetime import datetime, timedelta, timezone

from app.core.security import hash_interim_key
from app.modules.interim_keys.data.model import InterimKey
from app.modules.interim_keys.domain.usecases.revoke_interim_key import (
    RevokeInterimKeyUseCase,
)
from tests.conftest import FakeInterimKeyRepo


async def test_revoke_deletes_matching_key():
    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)
    raw = "the-raw-key"
    rec = InterimKey(user_id="u1", key_hash=hash_interim_key(raw), expires_at=now + timedelta(minutes=5))
    repo = FakeInterimKeyRepo([rec])
    uc = RevokeInterimKeyUseCase(repo=repo)

    assert await uc.execute(raw_key=raw) is True
    assert repo.items == {}


async def test_revoke_unknown_key_is_idempotent():
    uc = RevokeInterimKeyUseCase(repo=FakeInterimKeyRepo())
    assert await uc.execute(raw_key="nope") is False
