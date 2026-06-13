from datetime import datetime, timedelta, timezone

from app.modules.interim_keys.data.model import InterimKey
from tests.conftest import FakeInterimKeyRepo


async def test_fake_repo_respects_expiry():
    now = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)
    live = InterimKey(user_id="u1", key_hash="h_live", expires_at=now + timedelta(minutes=5))
    dead = InterimKey(user_id="u1", key_hash="h_dead", expires_at=now - timedelta(minutes=5))
    repo = FakeInterimKeyRepo([live, dead])
    assert (await repo.get_active_by_hash("h_live", now)).id == live.id
    assert await repo.get_active_by_hash("h_dead", now) is None
    assert await repo.delete_by_hash("h_live") is True
    assert await repo.delete_by_hash("missing") is False
