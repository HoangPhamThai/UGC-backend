# app/jobs/migrate_qc_products.py
"""Migration: a QC may now cover more than one product, so the user document
stores a `qc_products` array instead of the singular `qc_product`.

Idempotent. Runs automatically at startup (see app/app.py lifespan) and can also
be run standalone:

    python -m app.jobs.migrate_qc_products

Steps:
  1. For every user doc that still has the legacy scalar `qc_product`, move its
     value into a one-element `qc_products` array (unless one already exists),
     then unset `qc_product`.

After this runs, existing QC accounts load cleanly under the new User model
(which requires a non-empty `qc_products` when role=qc). Reads are ALSO resilient
to un-migrated docs via `User._coerce_legacy_qc_product`; this job cleans storage.
"""
import asyncio

from pymongo.asynchronous.database import AsyncDatabase

from app.core.db import mongo_connection
from app.modules.users.data.model import User


async def migrate_qc_products(db: AsyncDatabase) -> int:
    """Move legacy scalar `qc_product` into the `qc_products` array and unset the
    scalar. Idempotent — a second run matches no documents. Returns the count of
    documents migrated."""
    users = db[User.Config.collection_name]
    migrated = 0
    cursor = users.find(
        {"qc_product": {"$exists": True}},
        projection={"_id": 1, "qc_product": 1, "qc_products": 1},
    )
    async for doc in cursor:
        update: dict = {"$unset": {"qc_product": ""}}
        # Only seed qc_products from the scalar if it isn't already populated.
        if not doc.get("qc_products") and doc.get("qc_product"):
            update["$set"] = {"qc_products": [doc["qc_product"]]}
        await users.update_one({"_id": doc["_id"]}, update)
        migrated += 1
    return migrated


async def _run_cli() -> None:
    await mongo_connection.connect()
    db = await mongo_connection.get_db()
    migrated = await migrate_qc_products(db)
    print(f"[qc_products] total migrated: {migrated}")
    await mongo_connection.close()
    print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(_run_cli())
