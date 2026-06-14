from tests.conftest import FakeStatisticsRepo


async def test_email_map_returns_only_known_ids():
    repo = FakeStatisticsRepo(emails={"u1": "a@x.com", "u2": "b@x.com"})
    out = await repo.email_map({"u1", "u2", "missing"})
    assert out == {"u1": "a@x.com", "u2": "b@x.com"}


async def test_email_map_empty_input():
    repo = FakeStatisticsRepo(emails={"u1": "a@x.com"})
    assert await repo.email_map(set()) == {}
