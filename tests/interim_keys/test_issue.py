from datetime import datetime, timedelta, timezone

from app.core.security import hash_interim_key
from app.modules.interim_keys.domain.usecases.issue_interim_key import (
    IssueInterimKeyUseCase,
    INTERIM_KEY_TTL_MINUTES,
)
from tests.conftest import FakeInterimKeyRepo


async def test_issue_stores_hash_and_returns_raw_once():
    repo = FakeInterimKeyRepo()
    uc = IssueInterimKeyUseCase(repo=repo)
    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)

    issued = await uc.execute(user_id="u_admin", now=now)

    assert issued.raw_key
    assert issued.expires_at == now + timedelta(minutes=INTERIM_KEY_TTL_MINUTES)
    (stored,) = list(repo.items.values())
    assert stored.user_id == "u_admin"
    assert stored.key_hash == hash_interim_key(issued.raw_key)
    assert stored.key_hash != issued.raw_key
    assert stored.expires_at == issued.expires_at
