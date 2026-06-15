# app/modules/reports/data/repo.py
from datetime import datetime, timezone
from typing import Optional, override

from pymongo import ASCENDING, ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

from app.core.db import get_db
from app.core.logging_mixin import LoggerMixin
from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.repo import (
    AcceptanceReportRepo,
    EligibleArticle,
    ReportSourceRepo,
)
from app.modules.users.data.model import User
from app.modules.workspaces.data.model import Article, ArticleStatus, ExtractionStatus, Workspace


class ReportSourceDataRepository(LoggerMixin, ReportSourceRepo):
    async def _articles(self) -> AsyncCollection:
        db = await get_db()
        return db[Article.Config.collection_name]

    async def _users(self) -> AsyncCollection:
        db = await get_db()
        return db[User.Config.collection_name]

    @override
    async def list_eligible(
        self, *, start: datetime, end: datetime
    ) -> list[EligibleArticle]:
        pipeline: list[dict] = [
            {
                "$match": {
                    "status": ArticleStatus.APPROVED.value,
                    "link": {"$ne": None},
                    "extraction_status": ExtractionStatus.EXTRACTED.value,
                    "report_id": None,
                    "on_air_date": {"$gte": start, "$lte": end},
                }
            },
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
        coll = await self._articles()
        out: list[EligibleArticle] = []
        cursor = await coll.aggregate(pipeline)
        async for doc in cursor:
            article = Article.model_validate(doc)
            metrics = article.metrics
            out.append(
                EligibleArticle(
                    article_id=article.id,
                    owner_user_id=doc["_ws"]["owner_user_id"],
                    name=article.name,
                    product=article.product.value,
                    platform=(metrics.platform if metrics else None),
                    on_air_date=article.on_air_date,
                    link=article.link or "",
                    views=(metrics.views if metrics else None),
                )
            )
        return out

    @override
    async def creator_emails(self, ids: set[str]) -> dict[str, str]:
        if not ids:
            return {}
        coll = await self._users()
        out: dict[str, str] = {}
        async for doc in coll.find({"_id": {"$in": list(ids)}}, {"email": 1}):
            out[doc["_id"]] = doc["email"]
        return out


class AcceptanceReportDataRepository(LoggerMixin, AcceptanceReportRepo):
    def __init__(self) -> None:
        self.collection_name: str = AcceptanceReport.Config.collection_name

    async def _get_collection(self) -> AsyncCollection:
        db = await get_db()
        return db[self.collection_name]

    async def ensure_indexes(self) -> None:
        coll = await self._get_collection()
        # Migrate the legacy plain unique index to a partial one that ignores
        # amended (cancelled) reports, so a new report can be created for the
        # same (creator, period) after a final report is cancelled.
        try:
            await coll.drop_index("creator_user_id_1_period_1")
        except Exception:  # noqa: BLE001 — legacy index may be absent on fresh DBs
            pass
        # Drop the partial unique index too: its partialFilterExpression evolves
        # (e.g. adding REVIEWING), and Mongo refuses to redefine a same-named
        # index in place (IndexKeySpecsConflict). Recreate it below with the
        # current spec.
        try:
            await coll.drop_index("uniq_active_creator_period")
        except Exception:  # noqa: BLE001 — absent on fresh DBs or first migration
            pass
        await coll.create_index(
            [("creator_user_id", ASCENDING), ("period", ASCENDING)],
            unique=True,
            partialFilterExpression={
                "status": {"$in": [
                    ReportStatus.DRAFT.value,
                    ReportStatus.REVIEWING.value,
                    ReportStatus.FINAL.value,
                ]}
            },
            name="uniq_active_creator_period",
        )
        await coll.create_index([("period", ASCENDING), ("status", ASCENDING)])

    @override
    async def create(self, report: AcceptanceReport) -> AcceptanceReport:
        coll = await self._get_collection()
        await coll.insert_one(report.model_dump(by_alias=True))
        return report

    @override
    async def get_by_id(self, report_id: str) -> Optional[AcceptanceReport]:
        coll = await self._get_collection()
        doc = await coll.find_one({"_id": report_id})
        return AcceptanceReport.model_validate(doc) if doc else None

    @override
    async def get_by_creator_period(
        self, creator_user_id: str, period: str
    ) -> Optional[AcceptanceReport]:
        coll = await self._get_collection()
        doc = await coll.find_one(
            {
                "creator_user_id": creator_user_id,
                "period": period,
                "status": {"$in": [
                    ReportStatus.DRAFT.value,
                    ReportStatus.REVIEWING.value,
                    ReportStatus.FINAL.value,
                ]},
            }
        )
        return AcceptanceReport.model_validate(doc) if doc else None

    @override
    async def list(
        self,
        *,
        period: Optional[str],
        statuses: Optional[list[ReportStatus]],
        creator_user_id: Optional[str],
    ) -> list[AcceptanceReport]:
        coll = await self._get_collection()
        filt: dict = {}
        if period is not None:
            filt["period"] = period
        if statuses is not None:
            filt["status"] = {"$in": [s.value for s in statuses]}
        if creator_user_id is not None:
            filt["creator_user_id"] = creator_user_id
        cursor = coll.find(filt)  # ordering is the use-case's responsibility
        return [AcceptanceReport.model_validate(d) async for d in cursor]

    @override
    async def finalize(
        self, report_id: str, *, finalized_by: str
    ) -> Optional[AcceptanceReport]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": report_id},
            {
                "$set": {
                    "status": ReportStatus.FINAL.value,
                    "finalized_by": finalized_by,
                    "finalized_at": now,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return AcceptanceReport.model_validate(doc) if doc else None

    @override
    async def cancel(
        self, report_id: str, *, cancelled_by: str
    ) -> Optional[AcceptanceReport]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": report_id},
            {
                "$set": {
                    "status": ReportStatus.AMENDED.value,
                    "cancelled_by": cancelled_by,
                    "cancelled_at": now,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return AcceptanceReport.model_validate(doc) if doc else None

    @override
    async def delete(self, report_id: str) -> None:
        coll = await self._get_collection()
        await coll.delete_one({"_id": report_id})

    @override
    async def update_line_item_image(
        self, report_id: str, article_id: str, image_key: str
    ) -> Optional[AcceptanceReport]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": report_id, "line_items.article_id": article_id},
            {"$set": {"line_items.$.article_image": image_key, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        return AcceptanceReport.model_validate(doc) if doc else None

    @override
    async def submit(self, report_id: str) -> Optional[AcceptanceReport]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": report_id, "status": ReportStatus.DRAFT.value},
            {"$set": {"status": ReportStatus.REVIEWING.value, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        return AcceptanceReport.model_validate(doc) if doc else None

    @override
    async def approve(
        self, report_id: str, *, approved_by: str
    ) -> Optional[AcceptanceReport]:
        coll = await self._get_collection()
        now = datetime.now(timezone.utc)
        doc = await coll.find_one_and_update(
            {"_id": report_id, "status": ReportStatus.REVIEWING.value},
            {
                "$set": {
                    "status": ReportStatus.FINAL.value,
                    "finalized_by": approved_by,
                    "finalized_at": now,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return AcceptanceReport.model_validate(doc) if doc else None
