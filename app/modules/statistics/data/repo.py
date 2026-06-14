# app/modules/statistics/data/repo.py
import re
from datetime import datetime
from typing import Optional, override

from pymongo import ASCENDING
from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.users.data.model import User, UserRole
from app.modules.workspaces.data.model import (
    AnchorTargetType,
    Article,
    ArticleEvent,
    ArticleEventType,
    ArticleStatus,
    Feedback,
    FeedbackStatus,
    Product,
    Workspace,
)
from app.modules.statistics.domain.repo import (
    ArticleStat,
    CreatorRef,
    QcRef,
    StatisticsRepo,
)


class StatisticsDataRepository(LoggerMixin, StatisticsRepo):
    async def _articles(self) -> AsyncCollection:
        db = await get_db()
        return db[Article.Config.collection_name]

    async def _events(self) -> AsyncCollection:
        db = await get_db()
        return db[ArticleEvent.Config.collection_name]

    async def _users(self) -> AsyncCollection:
        db = await get_db()
        return db[User.Config.collection_name]

    async def _feedbacks(self) -> AsyncCollection:
        db = await get_db()
        return db[Feedback.Config.collection_name]

    async def _workspaces(self) -> AsyncCollection:
        db = await get_db()
        return db[Workspace.Config.collection_name]

    async def ensure_indexes(self) -> None:
        arts = await self._articles()
        await arts.create_index([("created_at", ASCENDING)])
        await arts.create_index([("status", ASCENDING)])
        await arts.create_index([("claimed_by", ASCENDING)])
        await arts.create_index([("reviewer_user_id", ASCENDING)])
        await arts.create_index([("product", ASCENDING)])
        await arts.create_index([("workspace_id", ASCENDING)])
        events = await self._events()
        await events.create_index([("type", ASCENDING), ("article_id", ASCENDING)])

    @override
    async def list_article_stats(
        self,
        *,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        product: Optional[Product] = None,
        creator_id: Optional[str] = None,
        include_not_submitted: bool,
    ) -> list[ArticleStat]:
        match: dict = {}
        created_at: dict = {}
        if from_dt is not None:
            created_at["$gte"] = from_dt
        if to_dt is not None:
            created_at["$lte"] = to_dt
        if created_at:
            match["created_at"] = created_at
        if product is not None:
            match["product"] = product.value
        if not include_not_submitted:
            match["status"] = {"$ne": ArticleStatus.NOT_SUBMITTED.value}

        pipeline: list[dict] = [{"$match": match}]
        # Resolve creator via the article's workspace owner.
        pipeline += [
            {
                "$lookup": {
                    "from": Workspace.Config.collection_name,
                    "localField": "workspace_id",
                    "foreignField": "_id",
                    "as": "_ws",
                }
            },
            {"$unwind": "$_ws"},
        ]
        if creator_id is not None:
            pipeline.append({"$match": {"_ws.owner_user_id": creator_id}})

        coll = await self._articles()
        out: list[ArticleStat] = []
        cursor = await coll.aggregate(pipeline)
        async for doc in cursor:
            article = Article.model_validate(doc)
            owner = doc["_ws"]["owner_user_id"]
            out.append(
                ArticleStat(
                    id=article.id,
                    name=article.name,
                    product=article.product,
                    status=article.status,
                    on_air_date=article.on_air_date,
                    created_at=article.created_at,
                    owner_user_id=owner,
                    claimed_by=article.claimed_by,
                    reviewer_user_id=article.reviewer_user_id,
                    rejected_by=article.rejected_by,
                    link=article.link,
                    metrics=article.metrics,
                )
            )
        return out

    @override
    async def auto_approved_article_ids(self) -> set[str]:
        coll = await self._events()
        ids = await coll.distinct(
            "article_id", {"type": ArticleEventType.AUTO_APPROVED.value}
        )
        return set(ids)

    @override
    async def list_creators(self, *, q: Optional[str]) -> list[CreatorRef]:
        query: dict = {"role": UserRole.CREATOR.value, "is_active": True}
        if q:
            query["email"] = {"$regex": re.escape(q), "$options": "i"}
        coll = await self._users()
        out: list[CreatorRef] = []
        async for doc in coll.find(query):
            out.append(CreatorRef(id=doc["_id"], email=doc["email"]))
        return out

    @override
    async def get_creator(self, creator_id: str) -> Optional[CreatorRef]:
        coll = await self._users()
        doc = await coll.find_one({"_id": creator_id, "role": UserRole.CREATOR.value})
        if doc is None:
            return None
        return CreatorRef(id=doc["_id"], email=doc["email"])

    @override
    async def list_qcs(self) -> list[QcRef]:
        coll = await self._users()
        out: list[QcRef] = []
        async for doc in coll.find({"role": UserRole.QC.value}):
            user = User.model_validate(doc)
            out.append(
                QcRef(id=user.id, email=user.email, products=list(user.qc_products))
            )
        return out

    @override
    async def email_map(self, ids: set[str]) -> dict[str, str]:
        if not ids:
            return {}
        coll = await self._users()
        out: dict[str, str] = {}
        async for doc in coll.find({"_id": {"$in": list(ids)}}, {"email": 1}):
            out[doc["_id"]] = doc["email"]
        return out

    @override
    async def get_article_with_owner(self, article_id: str):
        coll = await self._articles()
        doc = await coll.find_one({"_id": article_id})
        if doc is None:
            return None
        article = Article.model_validate(doc)
        ws_coll = await self._workspaces()
        ws = await ws_coll.find_one(
            {"_id": article.workspace_id}, {"owner_user_id": 1}
        )
        if ws is None:
            self.logger.warning("article %s has no workspace (orphaned)", article_id)
            owner = ""
        else:
            owner = ws["owner_user_id"]
        return article, owner

    @override
    async def feedback_counts(self, article_id: str):
        coll = await self._feedbacks()
        anchored = 0
        general = 0
        # Load and count via the model so legacy null anchors coerce to NONE,
        # matching the read-side semantics in ListFeedbacksUseCase.
        async for doc in coll.find(
            {"article_id": article_id, "status": {"$ne": FeedbackStatus.DRAFT.value}}
        ):
            fb = Feedback.model_validate(doc)
            if fb.anchor.target_type == AnchorTargetType.NONE:
                general += 1
            else:
                anchored += 1
        return anchored, general
