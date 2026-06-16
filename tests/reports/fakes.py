from typing import Optional

from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.repo import (
    AcceptanceReportRepo,
    EligibleArticle,
    ReportSourceRepo,
    TemplateMeta,
    TemplateRepo,
)


class FakeReportSourceRepo(ReportSourceRepo):
    def __init__(self, eligible: Optional[list[EligibleArticle]] = None,
                 emails: Optional[dict] = None) -> None:
        self._eligible = list(eligible or [])
        self._emails = dict(emails or {})

    async def list_eligible(self, *, start, end):
        return list(self._eligible)

    async def creator_emails(self, ids):
        return {i: self._emails[i] for i in ids if i in self._emails}


class FakeAcceptanceReportRepo(AcceptanceReportRepo):
    def __init__(self, reports: Optional[list[AcceptanceReport]] = None) -> None:
        self.items: dict[str, AcceptanceReport] = {r.id: r for r in (reports or [])}

    async def create(self, report):
        self.items[report.id] = report
        return report

    async def get_by_id(self, report_id):
        return self.items.get(report_id)

    async def get_by_creator_period(self, creator_user_id, period):
        return next(
            (r for r in self.items.values()
             if r.creator_user_id == creator_user_id and r.period == period
             and r.status in (ReportStatus.DRAFT, ReportStatus.REVIEWING, ReportStatus.FINAL)),
            None,
        )

    async def list(self, *, period, statuses, creator_user_id):
        out = list(self.items.values())
        if period is not None:
            out = [r for r in out if r.period == period]
        if statuses is not None:
            out = [r for r in out if r.status in statuses]
        if creator_user_id is not None:
            out = [r for r in out if r.creator_user_id == creator_user_id]
        return out

    async def finalize(self, report_id, *, finalized_by):
        r = self.items.get(report_id)
        if r is None:
            return None
        r.status = ReportStatus.FINAL
        r.finalized_by = finalized_by
        return r

    async def cancel(self, report_id, *, cancelled_by):
        r = self.items.get(report_id)
        if r is None:
            return None
        r.status = ReportStatus.AMENDED
        r.cancelled_by = cancelled_by
        return r

    async def delete(self, report_id):
        self.items.pop(report_id, None)

    async def update_line_item_image(self, report_id, article_id, image_key):
        r = self.items.get(report_id)
        if r is None:
            return None
        for li in r.line_items:
            if li.article_id == article_id:
                li.article_image = image_key
        return r

    async def submit(self, report_id):
        r = self.items.get(report_id)
        if r is None:
            return None
        r.status = ReportStatus.REVIEWING
        return r

    async def approve(self, report_id, *, approved_by):
        r = self.items.get(report_id)
        if r is None:
            return None
        r.status = ReportStatus.FINAL
        r.finalized_by = approved_by
        return r


class FakeTemplateRepo(TemplateRepo):
    def __init__(self, active_bytes=None):
        self._bytes = active_bytes

    async def get_meta(self):
        return TemplateMeta(filename="tpl.docx", uploaded_by="u", uploaded_at=None) if self._bytes else None

    async def get_active_bytes(self):
        return self._bytes

    async def save(self, *, data, filename, uploaded_by):
        self._bytes = data
        return TemplateMeta(filename=filename, uploaded_by=uploaded_by, uploaded_at=None)


def make_eligible(article_id="art_1", owner="u_creator", views=100) -> EligibleArticle:
    from datetime import date
    return EligibleArticle(
        article_id=article_id, owner_user_id=owner, name="A", product="CL",
        platform="tiktok", on_air_date=date(2026, 6, 1),
        link=f"https://x/{article_id}", views=views,
    )


class RecordingEmailService:
    """Duck-typed stand-in for EmailService that records report email schedules."""

    def __init__(self) -> None:
        self.report_events: list[tuple] = []

    def schedule_report_event(self, *, event, period, creator_user_id) -> None:
        self.report_events.append((event, period, creator_user_id))
