# app/modules/workspaces/data/repo.py
from datetime import datetime, timezone
from typing import Optional, override

from pymongo import ASCENDING, ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.workspaces.data.model import Article, ArticleStatus, Product, Workspace
from app.modules.workspaces.domain.errors import WorkspaceNameTakenError
from app.modules.workspaces.domain.repo import ArticleRepo, WorkspaceRepo


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
        await coll.create_index(
            [("owner_user_id", ASCENDING), ("name_lower", ASCENDING)],
            unique=True,
            name="uniq_owner_name_lower",
        )

    @override
    async def create(self, workspace: Workspace) -> Workspace:
        coll = await self._get_collection()
        # Repo owns name_lower normalization; callers never set it.
        workspace.name_lower = workspace.name.casefold()
        payload = workspace.model_dump(by_alias=True)
        try:
            await coll.insert_one(payload)
        except DuplicateKeyError:
            raise WorkspaceNameTakenError()
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
    async def list_with_product(
        self, product: Product, *, skip: int, limit: int
    ) -> list[Workspace]:
        # Find workspace ids that have at least one article of `product`.
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        ids = await article_coll.distinct(
            "workspace_id", {"product": product.value}
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
    async def count_with_product(self, product: Product) -> int:
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        ids = await article_coll.distinct(
            "workspace_id", {"product": product.value}
        )
        return len(ids)

    @override
    async def delete(self, workspace_id: str) -> None:
        coll = await self._get_collection()
        await coll.delete_one({"_id": workspace_id})

    @override
    async def article_counts(
        self, workspace_ids: list[str], *, product: Optional[Product] = None
    ) -> dict[str, int]:
        if not workspace_ids:
            return {}
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        match: dict = {"workspace_id": {"$in": workspace_ids}}
        if product is not None:
            match["product"] = product.value
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
    async def products_for(self, workspace_ids: list[str]) -> dict[str, list[Product]]:
        if not workspace_ids:
            return {}
        db = await get_db()
        article_coll = db[Article.Config.collection_name]
        pipeline = [
            {"$match": {"workspace_id": {"$in": workspace_ids}}},
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
        await coll.create_index([("workspace_id", ASCENDING), ("created_at", ASCENDING)])
        await coll.create_index([("workspace_id", ASCENDING), ("product", ASCENDING)])
        await coll.create_index([("product", ASCENDING), ("status", ASCENDING)])

    @override
    async def create(self, article: Article) -> Article:
        coll = await self._get_collection()
        payload = article.model_dump(by_alias=True)
        await coll.insert_one(payload)
        return article

    @override
    async def get_by_id(self, article_id: str) -> Optional[Article]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": article_id})
        return Article.model_validate(doc) if doc else None

    @override
    async def list_by_workspace(
        self, workspace_id: str, *, product: Optional[Product] = None
    ) -> list[Article]:
        coll = await self._get_collection()
        filt: dict = {"workspace_id": workspace_id}
        if product is not None:
            filt["product"] = product.value
        cursor = coll.find(filt).sort("created_at", ASCENDING)
        docs = [doc async for doc in cursor]
        return [Article.model_validate(d) for d in docs]

    @override
    async def workspace_has_product(self, workspace_id: str, product: Product) -> bool:
        coll = await self._get_collection()
        doc = await coll.find_one(
            {"workspace_id": workspace_id, "product": product.value},
            projection={"_id": 1},
        )
        return doc is not None

    @override
    async def update_content(self, article_id: str, content: str) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": article_id},
            {"$set": {"content": content, "updated_at": now}},
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
    ) -> Optional[Article]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        update: dict = {"status": status.value, "updated_at": now}
        if reviewer_user_id is not None:
            update["reviewer_user_id"] = reviewer_user_id
        if set_reviewed_at:
            update["reviewed_at"] = now
        doc = await coll.find_one_and_update(
            {"_id": article_id},
            {"$set": update},
            return_document=ReturnDocument.AFTER,
        )
        return Article.model_validate(doc) if doc else None

    @override
    async def delete(self, article_id: str) -> None:
        coll = await self._get_collection()
        await coll.delete_one({"_id": article_id})

    @override
    async def delete_by_workspace(self, workspace_id: str) -> int:
        coll = await self._get_collection()
        result = await coll.delete_many({"workspace_id": workspace_id})
        return result.deleted_count
