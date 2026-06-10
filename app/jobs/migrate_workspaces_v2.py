# app/jobs/migrate_workspaces_v2.py
"""One-off migration that brings existing data in line with the doc-synced
workspaces module. Run ONCE, BEFORE deploying the new code.

    python -m app.jobs.migrate_workspaces_v2

Steps (idempotent):
  1. Status remap: waiting_for_review -> submitted; reviewing -> submitted
     (the "reviewing" claim step is removed; an in-review article reverts to
     awaiting-QC).
  2. Backfill on_air_date for articles missing it: set to created_at's date
     (stored midnight-UTC, matching the runtime encoding).
  3. Drop the legacy unique index 'uniq_owner_name_lower' on workspaces
     (names are no longer unique).
  4. Unset the now-removed 'name_lower' field on workspace docs.
"""
import asyncio
from datetime import datetime, time, timezone

from app.core.db import mongo_connection
from app.modules.workspaces.data.model import Article, Workspace


def _midnight_utc(dt: datetime) -> datetime:
    """Date part of `dt` at midnight UTC (handles naive or aware input)."""
    return datetime.combine(dt.date(), time.min, tzinfo=timezone.utc)


async def migrate() -> None:
    await mongo_connection.connect()
    db = await mongo_connection.get_db()
    articles = db[Article.Config.collection_name]
    workspaces = db[Workspace.Config.collection_name]

    # 1. Status remap.
    for legacy in ("waiting_for_review", "reviewing"):
        res = await articles.update_many(
            {"status": legacy}, {"$set": {"status": "submitted"}}
        )
        print(f"[status] {legacy} -> submitted: {res.modified_count}")

    # 2. Backfill on_air_date = date(created_at), midnight UTC.
    backfilled = 0
    cursor = articles.find(
        {"on_air_date": {"$exists": False}}, projection={"_id": 1, "created_at": 1}
    )
    async for doc in cursor:
        created = doc.get("created_at")
        if not isinstance(created, datetime):
            created = datetime.now(timezone.utc)
        await articles.update_one(
            {"_id": doc["_id"]},
            {"$set": {"on_air_date": _midnight_utc(created)}},
        )
        backfilled += 1
        print(f"[on_air_date] backfilled {doc['_id']}")
    print(f"[on_air_date] total backfilled: {backfilled}")

    # 3. Drop legacy unique index (ignore if already absent).
    try:
        await workspaces.drop_index("uniq_owner_name_lower")
        print("[index] dropped uniq_owner_name_lower")
    except Exception as e:  # OperationFailure when the index doesn't exist
        print(f"[index] uniq_owner_name_lower not dropped ({type(e).__name__}: {e})")

    # 4. Remove vestigial name_lower field.
    res = await workspaces.update_many(
        {"name_lower": {"$exists": True}}, {"$unset": {"name_lower": ""}}
    )
    print(f"[name_lower] unset on {res.modified_count} workspaces")

    await mongo_connection.close()
    print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
