# app/jobs/migrate_qc_products.py
"""One-off migration: a QC may now cover more than one product, so the user
document stores a `qc_products` array instead of the singular `qc_product`.
Run ONCE, BEFORE (or right alongside) deploying the new code.

    python -m app.jobs.migrate_qc_products

Steps (idempotent):
  1. For every user doc that still has the legacy scalar `qc_product`, move its
     value into a one-element `qc_products` array (unless one already exists),
     then unset `qc_product`.

After this runs, existing QC accounts load cleanly under the new User model
(which requires a non-empty `qc_products` when role=qc).
"""
import asyncio

from app.core.db import mongo_connection
from app.modules.users.data.model import User


async def migrate() -> None:
    await mongo_connection.connect()
    db = await mongo_connection.get_db()
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
        print(f"[qc_products] migrated {doc['_id']}")
    print(f"[qc_products] total migrated: {migrated}")

    await mongo_connection.close()
    print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
