import pytest

from app.modules.reports.data.template_repo import (
    TEMPLATE_OBJECT_KEY,
    TemplateDataRepository,
)
from app.modules.reports.storage import InMemoryObjectStorage


class FakeMetaStore:
    """Stands in for the Mongo meta collection."""
    def __init__(self):
        self.doc = None

    async def find_one(self, _filter):
        return self.doc

    async def replace_one(self, _filter, doc, upsert=False):
        self.doc = doc


@pytest.mark.asyncio
async def test_save_and_get_active_bytes_and_meta():
    storage = InMemoryObjectStorage()
    repo = TemplateDataRepository(storage=storage, meta=FakeMetaStore())

    assert await repo.get_active_bytes() is None  # nothing uploaded yet
    assert (await repo.get_meta()) is None

    meta = await repo.save(data=b"DOCX", filename="tpl.docx", uploaded_by="u_admin")
    assert meta.filename == "tpl.docx"
    assert meta.uploaded_by == "u_admin"
    assert await repo.get_active_bytes() == b"DOCX"
    assert await storage.get(TEMPLATE_OBJECT_KEY) == b"DOCX"

    again = await repo.get_meta()
    assert again is not None and again.filename == "tpl.docx"
