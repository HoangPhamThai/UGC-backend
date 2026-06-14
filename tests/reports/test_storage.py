import pytest

from app.modules.reports.storage import InMemoryObjectStorage


@pytest.mark.asyncio
async def test_put_get_roundtrip():
    s = InMemoryObjectStorage()
    await s.put("reports/2026-06/rpt_1.docx", b"hello", content_type="application/x")
    assert await s.get("reports/2026-06/rpt_1.docx") == b"hello"


@pytest.mark.asyncio
async def test_delete_removes_object():
    s = InMemoryObjectStorage()
    await s.put("k", b"x", content_type="application/x")
    await s.delete("k")
    with pytest.raises(KeyError):
        await s.get("k")
