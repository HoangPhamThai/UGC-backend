import pytest

from app.modules.reports.data.rules_repo import ReportRulesDataRepository


class _FakeColl:
    def __init__(self):
        self.doc = None

    async def find_one(self, q):
        return self.doc

    async def replace_one(self, q, doc, upsert=False):
        self.doc = doc


async def test_get_none_when_empty():
    repo = ReportRulesDataRepository(coll=_FakeColl())
    assert await repo.get_active() is None


async def test_save_then_get_roundtrip():
    repo = ReportRulesDataRepository(coll=_FakeColl())
    await repo.save_active(
        source_markdown="rules text",
        ir={"version": 1, "rules": []},
        warnings=[],
        status="ok",
        updated_by="u_admin",
    )
    got = await repo.get_active()
    assert got["source_markdown"] == "rules text"
    assert got["status"] == "ok"
