# app/modules/reports/data/template_repo.py
from datetime import datetime, timezone
from typing import Optional, override

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.reports.domain.repo import TemplateMeta, TemplateRepo
from app.modules.reports.storage import ObjectStorage

TEMPLATE_OBJECT_KEY = "templates/acceptance_report/active.docx"
_META_COLLECTION = "report_templates"
_META_ID = "active"


class TemplateDataRepository(LoggerMixin, TemplateRepo):
    """Active template = bytes in object storage + a single Mongo meta doc.
    `meta` is injected in tests; in production it is the Mongo collection."""

    def __init__(self, *, storage: ObjectStorage, meta=None) -> None:
        self._storage = storage
        self._meta = meta

    async def _meta_coll(self):
        if self._meta is not None:
            return self._meta
        db = await get_db()
        return db[_META_COLLECTION]

    @override
    async def get_meta(self) -> Optional[TemplateMeta]:
        coll = await self._meta_coll()
        doc = await coll.find_one({"_id": _META_ID})
        if not doc:
            return None
        return TemplateMeta(
            filename=doc["filename"],
            uploaded_by=doc.get("uploaded_by"),
            uploaded_at=doc.get("uploaded_at"),
        )

    @override
    async def get_active_bytes(self) -> Optional[bytes]:
        if await self.get_meta() is None:
            return None
        try:
            return await self._storage.get(TEMPLATE_OBJECT_KEY)
        except KeyError:
            return None

    @override
    async def save(self, *, data: bytes, filename: str, uploaded_by: str) -> TemplateMeta:
        await self._storage.put(
            TEMPLATE_OBJECT_KEY,
            data,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        now = datetime.now(timezone.utc)
        coll = await self._meta_coll()
        await coll.replace_one(
            {"_id": _META_ID},
            {"_id": _META_ID, "filename": filename, "uploaded_by": uploaded_by, "uploaded_at": now},
            upsert=True,
        )
        return TemplateMeta(filename=filename, uploaded_by=uploaded_by, uploaded_at=now)
