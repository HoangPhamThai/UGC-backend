# app/modules/workspaces/data/repo.py
from datetime import date, datetime, timezone
from typing import Optional, override

from pymongo import ASCENDING, ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.core.time import date_to_storage
from app.modules.workspaces.data.model import (
    Article,
    ArticleEvent,
    ArticleStatus,
    AWAITING_QC_STATUSES,
    ExtractionStatus,
    Feedback,
    FeedbackReply,
    FeedbackStatus,
    PostMetrics,
    Product,
    Workspace,
)
from app.modules.workspaces.domain.repo import (
    ArticleEventRepo,
    ArticleRepo,
    FeedbackRepo,
    WorkspaceRepo,
)


# --- Workspaces ---


class WorkspaceDataRepository(LoggerMixin, WorkspaceRepo):
    def __init__(self) -> None:
        self.collection_name: str = Workspace.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("owner_user_id", ASCENDING)])
        # Note: workspace names are intentionally NOT unique (workspace.md §2.1,
        # §7). The legacy "uniq_owner_name_lower" index is dropped by the v2
        # migration (app/jobs/migrate_workspaces_v2.py).

    @override
    async def create(self, workspace: Workspace) -> Workspace:
        coll = await self._get_collection()
        payload = workspace.model_dump(by_alias=True)
        await coll.insert_one(payload)
        return workspace

    @override
    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": workspace_id})
        return Workspace.model_validate(doc) if doc else None

    @override
    async def list_by_owner(
        self, owner_user_id: str, *, skip: int, limit: int
    ) -> list[Workspace]:
        coll = await self._get_collection()
        cursor = (
            coll.find({"owner_user_id": owner_user_id})
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = [doc async for doc in cursor]
        return [Workspace.model_validate(d) for d in docs]

    @override
    async def count_by_owner(self, owner_user_id: str) -> int:
        coll = await self._get_collection()
        return await coll.count_documents({"owner_user_id": owner_user_id})

    @override
    async def list_all(self, *, skip: int, limit: int) -> list[Workspace]:
        coll = await self._get_collection()
        cursor = coll.find({}).sort("updated_at", -1).skip(skip).limit(limit)
        docs = [doc async for doc in cursor]
        return [Workspace.model_validate(d) for d in docs]

    @override
    async def count_all(self) -> int:
        coll = await self._get_collection()
        return await coll.count_documents({})

    @override
    async def list_with_products(
        self, products: list[Product], *, skip: int, limit: int
    ) -> list[Workspace]:
        # Find workspace ids that have at least one article of any `products`.
        if not products:
            return []
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        ids = await article_coll.distinct(
            "workspace_id", {"product": {"$in": [p.value for p in products]}}
        )
        if not ids:
            return []
        coll = await self._get_collection()
        cursor = (
            coll.find({"_id": {"$in": ids}})
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = [doc async for doc in cursor]
        return [Workspace.model_validate(d) for d in docs]

    @override
    async def count_with_products(self, products: list[Product]) -> int:
        if not products:
            return 0
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        ids = await article_coll.distinct(
            "workspace_id", {"product": {"$in": [p.value for p in products]}}
        )
        return len(ids)

    @override
    async def delete(self, workspace_id: str) -> None:
        coll = await self._get_collection()
        await coll.delete_one({"_id": workspace_id})

    @override
    async def increment_article_count(self, workspace_id: str, *, by: int = 1) -> None:
        coll = await self._get_collection()
        # On decrement, require the current count to be at least `|by|` so we
        # never write a negative value. On increment, no extra filter needed.
        filt: dict = {"_id": workspace_id}
        if by < 0:
            filt["article_count"] = {"$gte": -by}
        await coll.update_one(filt, {"$inc": {"article_count": by}})

    @override
    async def article_counts(
        self, workspace_ids: list[str], *, products: Optional[list[Product]] = None
    ) -> dict[str, int]:
        if not workspace_ids:
            return {}
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        match: dict = {"workspace_id": {"$in": workspace_ids}}
        if products is not None:
            match["product"] = {"$in": [p.value for p in products]}
        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$workspace_id", "c": {"$sum": 1}}},
        ]
        result: dict[str, int] = {wid: 0 for wid in workspace_ids}
        cursor = await article_coll.aggregate(pipeline)
        async for row in cursor:
            result[row["_id"]] = row["c"]
        return result

    @override
    async def products_for(
        self, workspace_ids: list[str], *, restrict: Optional[list[Product]] = None
    ) -> dict[str, list[Product]]:
        if not workspace_ids:
            return {}
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        match: dict = {"workspace_id": {"$in": workspace_ids}}
        if restrict is not None:
            match["product"] = {"$in": [p.value for p in restrict]}
        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$workspace_id", "products": {"$addToSet": "$product"}}},
        ]
        result: dict[str, list[Product]] = {wid: [] for wid in workspace_ids}
        cursor = await article_coll.aggregate(pipeline)
        async for row in cursor:
            result[row["_id"]] = sorted(
                (Product(p) for p in row["products"]),
                key=lambda p: list(Product).index(p),
            )
        return result


# --- Articles ---


class ArticleDataRepository(LoggerMixin, ArticleRepo):
    def __init__(self) -> None:
        self.collection_name: str = Article.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index(
            [("workspace_id", ASCENDING), ("created_at", ASCENDING)]
        )
        await coll.create_index([("workspace_id", ASCENDING), ("product", ASCENDING)])
        await coll.create_index([("product", ASCENDING), ("status", ASCENDING)])
        await coll.create_index([("status", ASCENDING), ("on_air_date", ASCENDING)])

    @override
    async def create(self, article: Article) -> Article:
        coll = await self._get_collection()
        payload = article.model_dump(by_alias=True)
        # bson cannot encode a bare date; store on_air_date as midnight-UTC.
        payload["on_air_date"] = date_to_storage(article.on_air_date)
        await coll.insert_one(payload)
        return article

    @override
    async def get_by_id(self, article_id: str) -> Optional[Article]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": article_id})
        return Article.model_validate(doc) if doc else None

    @override
    async def list_by_workspace(
        self, workspace_id: str, *, products: Optional[list[Product]] = None
    ) -> list[Article]:
        coll = await self._get_collection()
        filt: dict = {"workspace_id": workspace_id}
        if products is not None:
            filt["product"] = {"$in": [p.value for p in products]}
        cursor = coll.find(filt).sort("created_at", ASCENDING)
        docs = [doc async for doc in cursor]
        return [Article.model_validate(d) for d in docs]

    @override
    async def workspace_has_any_product(
        self, workspace_id: str, products: list[Product]
    ) -> bool:
        if not products:
            return False
        coll = await self._get_collection()
        doc = await coll.find_one(
            {
                "workspace_id": workspace_id,
                "product": {"$in": [p.value for p in products]},
            },
            projection={"_id": 1},
        )
        return doc is not None

    @override
    async def update_fields(
        self,
        article_id: str,
        *,
        name: Optional[str] = None,
        product: Optional[Product] = None,
        on_air_date: Optional[date] = None,
        content: Optional[str] = None,
    ) -> Optional[Article]:
        coll = await self._get_collection()
        set_doc: dict = {"updated_at": datetime.now(timezone.utc)}
        if name is not None:
            set_doc["name"] = name
        if product is not None:
            set_doc["product"] = product.value
        if on_air_date is not None:
            set_doc["on_air_date"] = date_to_storage(on_air_date)
        if content is not None:
            set_doc["content"] = content
        doc = await coll.find_one_and_update(
            {"_id": article_id},
            {"$set": set_doc},
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def set_link(
        self, article_id: str, *, link: str, link_edit_count: int
    ) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": article_id},
            {
                "$set": {
                    "link": link,
                    "link_submitted_at": now,
                    "link_edit_count": link_edit_count,
                    "updated_at": now,
                    "extraction_status": ExtractionStatus.PENDING.value,
                    "extraction_error": None,
                    "extraction_attempts": 0,
                    "extracted_at": None,
                    "metrics": None,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def set_report_id(
        self, article_id: str, report_id: Optional[str]
    ) -> Optional[Article]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": article_id},
            {"$set": {"report_id": report_id, "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def record_extraction_success(
        self, article_id: str, *, url: str, metrics: PostMetrics
    ) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": article_id, "link": url},
            {
                "$set": {
                    "metrics": metrics.model_dump(),
                    "extraction_status": ExtractionStatus.EXTRACTED.value,
                    "extracted_at": now,
                    "extraction_error": None,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def record_extraction_failure(
        self, article_id: str, *, url: str, error: str
    ) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": article_id, "link": url},
            {
                "$set": {
                    "extraction_status": ExtractionStatus.FAILED.value,
                    "extraction_error": error,
                    "updated_at": now,
                },
                "$inc": {"extraction_attempts": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def set_extraction_pending(self, article_id: str) -> Optional[Article]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": article_id},
            {
                "$set": {
                    "extraction_status": ExtractionStatus.PENDING.value,
                    "extraction_error": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def update_status(
        self,
        article_id: str,
        *,
        status: ArticleStatus,
        reviewer_user_id: Optional[str] = None,
        set_reviewed_at: bool = False,
        last_activity_by: Optional[str] = None,
        increment_review_round: bool = False,
        reviewed_content: Optional[str] = None,
        clear_reviewed_content: bool = False,
    ) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        set_doc: dict = {"status": status.value, "updated_at": now}
        if reviewer_user_id is not None:
            set_doc["reviewer_user_id"] = reviewer_user_id
        if set_reviewed_at:
            set_doc["reviewed_at"] = now
        if last_activity_by is not None:
            set_doc["last_activity_by"] = last_activity_by
            set_doc["last_activity_at"] = now
        if clear_reviewed_content:
            set_doc["reviewed_content"] = None
        elif reviewed_content is not None:
            set_doc["reviewed_content"] = reviewed_content
        update: dict = {"$set": set_doc}
        if increment_review_round:
            update["$inc"] = {"review_round": 1}
        doc = await coll.find_one_and_update(
            {"_id": article_id}, update, return_document=ReturnDocument.AFTER
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def claim(self, article_id: str, qc_user_id: str) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        # Conditional update: only claim when currently unclaimed AND awaiting QC.
        # The status guard closes the TOCTOU window where a concurrent withdraw
        # could flip the article to not_submitted between the use-case read and
        # this update, which would otherwise leave a stale claim on a non-review
        # article that persists across resubmit.
        doc = await coll.find_one_and_update(
            {
                "_id": article_id,
                "claimed_by": None,
                "status": {"$in": [s.value for s in AWAITING_QC_STATUSES]},
            },
            {"$set": {"claimed_by": qc_user_id, "claimed_at": now, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def withdraw(self, article_id: str, *, actor_id: str) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        # Atomic: only withdraw while still submitted AND unclaimed.
        doc = await coll.find_one_and_update(
            {
                "_id": article_id,
                "status": ArticleStatus.SUBMITTED.value,
                "claimed_by": None,
            },
            {
                "$set": {
                    "status": ArticleStatus.NOT_SUBMITTED.value,
                    "last_activity_by": actor_id,
                    "last_activity_at": now,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def touch_activity(self, article_id: str, *, actor_id: str) -> None:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        await coll.update_one(
            {"_id": article_id},
            {
                "$set": {
                    "last_activity_by": actor_id,
                    "last_activity_at": now,
                    "updated_at": now,
                }
            },
        )

    @override
    async def reject(
        self, article_id: str, *, reviewer_user_id: str, reason: str
    ) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": article_id},
            {
                "$set": {
                    "status": ArticleStatus.REJECTED.value,
                    "reviewer_user_id": reviewer_user_id,
                    "reviewed_at": now,
                    "reject_reason": reason,
                    "rejected_by": reviewer_user_id,
                    "rejected_at": now,
                    "last_activity_by": reviewer_user_id,
                    "last_activity_at": now,
                    "updated_at": now,
                    "reviewed_content": None,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    def _product_status_filter(
        self, products: Optional[list[Product]], statuses: Optional[list[ArticleStatus]]
    ) -> dict:
        filt: dict = {}
        if products is not None:
            filt["product"] = {"$in": [p.value for p in products]}
        if statuses is not None:
            filt["status"] = {"$in": [s.value for s in statuses]}
        return filt

    @override
    async def list_by_products(
        self, products, *, statuses, skip, limit
    ) -> list[Article]:
        coll = await self._get_collection()
        cursor = (
            coll.find(self._product_status_filter(products, statuses))
            .sort([("on_air_date", ASCENDING), ("created_at", ASCENDING)])
            .skip(skip)
            .limit(limit)
        )
        docs = [doc async for doc in cursor]
        return [Article.model_validate(d) for d in docs]

    @override
    async def count_by_products(self, products, *, statuses) -> int:
        coll = await self._get_collection()
        return await coll.count_documents(
            self._product_status_filter(products, statuses)
        )

    @override
    async def delete(self, article_id: str) -> None:
        coll = await self._get_collection()
        await coll.delete_one({"_id": article_id})

    @override
    async def delete_by_workspace(self, workspace_id: str) -> int:
        coll = await self._get_collection()
        result = await coll.delete_many({"workspace_id": workspace_id})
        return result.deleted_count


class FeedbackDataRepository(LoggerMixin, FeedbackRepo):
    def __init__(self) -> None:
        self.collection_name: str = Feedback.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("article_id", ASCENDING), ("status", ASCENDING)])

    @override
    async def create(self, feedback: Feedback) -> Feedback:
        coll = await self._get_collection()
        await coll.insert_one(feedback.model_dump(by_alias=True))
        return feedback

    @override
    async def get_by_id(self, feedback_id: str) -> Optional[Feedback]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": feedback_id})
        return Feedback.model_validate(doc) if doc else None

    @override
    async def list_by_article(
        self, article_id: str, *, statuses: Optional[list[FeedbackStatus]] = None
    ) -> list[Feedback]:
        coll = await self._get_collection()
        filt: dict = {"article_id": article_id}
        if statuses is not None:
            filt["status"] = {"$in": [s.value for s in statuses]}
        cursor = coll.find(filt).sort("created_at", ASCENDING)
        docs = [doc async for doc in cursor]
        return [Feedback.model_validate(d) for d in docs]

    @override
    async def set_status(
        self,
        feedback_id: str,
        *,
        status: FeedbackStatus,
        resolved_by: Optional[str] = None,
        set_resolved_at: bool = False,
        clear_resolved: bool = False,
    ) -> Optional[Feedback]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        set_doc: dict = {"status": status.value, "updated_at": now}
        if resolved_by is not None:
            set_doc["resolved_by"] = resolved_by
        if set_resolved_at:
            set_doc["resolved_at"] = now
        update: dict = {"$set": set_doc}
        if clear_resolved:
            update["$set"].pop("resolved_by", None)
            update["$set"].pop("resolved_at", None)
            update["$unset"] = {"resolved_by": "", "resolved_at": ""}
        doc = await coll.find_one_and_update(
            {"_id": feedback_id}, update, return_document=ReturnDocument.AFTER
        )
        return Feedback.model_validate(doc) if doc else None

    @override
    async def mark_drafts_open(self, article_id: str) -> int:
        coll = await self._get_collection()
        result = await coll.update_many(
            {"article_id": article_id, "status": FeedbackStatus.DRAFT.value},
            {
                "$set": {
                    "status": FeedbackStatus.OPEN.value,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count

    @override
    async def add_reply(
        self, feedback_id: str, reply: FeedbackReply
    ) -> Optional[Feedback]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": feedback_id},
            {
                "$push": {"replies": reply.model_dump()},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )
        return Feedback.model_validate(doc) if doc else None

    @override
    async def count_open(self, article_id: str) -> int:
        coll = await self._get_collection()
        return await coll.count_documents(
            {"article_id": article_id, "status": FeedbackStatus.OPEN.value}
        )

    @override
    async def update_body(self, feedback_id: str, body: str) -> Optional[Feedback]:
        coll = await self._get_collection()
        doc = await coll.find_one_and_update(
            {"_id": feedback_id},
            {"$set": {"body": body, "updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        return Feedback.model_validate(doc) if doc else None

    @override
    async def delete(self, feedback_id: str) -> bool:
        coll = await self._get_collection()
        result = await coll.delete_one({"_id": feedback_id})
        return result.deleted_count > 0


class ArticleEventDataRepository(LoggerMixin, ArticleEventRepo):
    def __init__(self) -> None:
        self.collection_name: str = ArticleEvent.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        await coll.create_index([("article_id", ASCENDING), ("created_at", ASCENDING)])

    @override
    async def create(self, event: ArticleEvent) -> ArticleEvent:
        coll = await self._get_collection()
        await coll.insert_one(event.model_dump(by_alias=True))
        return event
