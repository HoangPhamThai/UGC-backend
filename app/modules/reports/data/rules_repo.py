from datetime import datetime, timezone
from typing import Optional, override

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.reports.domain.repo import ReportRulesRepo

_COLLECTION = "report_rules"
_DOC_ID = "active"


class ReportRulesDataRepository(LoggerMixin, ReportRulesRepo):
    """`coll` is injected in tests; in production it is the Mongo collection."""

    def __init__(self, *, coll=None) -> None:
        self._coll = coll

    async def _collection(self):
        if self._coll is not None:
            return self._coll
        db = await get_db()
        return db[_COLLECTION]

    @override
    async def get_active(self) -> Optional[dict]:
        coll = await self._collection()
        return await coll.find_one({"_id": _DOC_ID})

    @override
    async def save_active(
        self, *, source_markdown: str, ir: dict, warnings: list[dict],
        status: str, updated_by: str,
    ) -> dict:
        now = datetime.now(timezone.utc)
        doc = {
            "_id": _DOC_ID, "source_markdown": source_markdown, "ir": ir,
            "warnings": warnings, "status": status, "updated_by": updated_by,
            "updated_at": now,
        }
        coll = await self._collection()
        await coll.replace_one({"_id": _DOC_ID}, doc, upsert=True)
        return doc
