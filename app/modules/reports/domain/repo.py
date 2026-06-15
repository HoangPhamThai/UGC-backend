# app/modules/reports/domain/repo.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.modules.reports.data.model import AcceptanceReport, ReportStatus


@dataclass(frozen=True)
class EligibleArticle:
    """An approved+linked+extracted, not-yet-reported article in the period,
    attributed to its creator (workspace owner)."""
    article_id: str
    owner_user_id: str
    name: str
    product: str
    platform: Optional[str]
    on_air_date: date
    link: str
    views: Optional[int]


@dataclass(frozen=True)
class TemplateMeta:
    filename: str
    uploaded_by: Optional[str]
    uploaded_at: Optional[datetime]


class TemplateRepo(ABC):
    @abstractmethod
    async def get_meta(self) -> Optional[TemplateMeta]:
        """Active uploaded template metadata, or None when only the default exists."""
        ...

    @abstractmethod
    async def get_active_bytes(self) -> Optional[bytes]:
        """Uploaded template bytes, or None when only the default exists."""
        ...

    @abstractmethod
    async def save(self, *, data: bytes, filename: str, uploaded_by: str) -> TemplateMeta:
        ...


class ReportSourceRepo(ABC):
    @abstractmethod
    async def list_eligible(
        self, *, start: datetime, end: datetime
    ) -> list[EligibleArticle]:
        """Eligible articles whose on_air_date is within [start, end]."""
        ...

    @abstractmethod
    async def creator_emails(self, ids: set[str]) -> dict[str, str]:
        """Map creator ids to emails (missing ids omitted)."""
        ...


class AcceptanceReportRepo(ABC):
    @abstractmethod
    async def create(self, report: AcceptanceReport) -> AcceptanceReport: ...

    @abstractmethod
    async def get_by_id(self, report_id: str) -> Optional[AcceptanceReport]: ...

    @abstractmethod
    async def get_by_creator_period(
        self, creator_user_id: str, period: str
    ) -> Optional[AcceptanceReport]: ...

    @abstractmethod
    async def list(
        self,
        *,
        period: Optional[str],
        statuses: Optional[list[ReportStatus]],
        creator_user_id: Optional[str],
    ) -> list[AcceptanceReport]: ...

    @abstractmethod
    async def finalize(
        self, report_id: str, *, finalized_by: str
    ) -> Optional[AcceptanceReport]: ...

    @abstractmethod
    async def cancel(
        self, report_id: str, *, cancelled_by: str
    ) -> Optional[AcceptanceReport]: ...

    @abstractmethod
    async def delete(self, report_id: str) -> None: ...
