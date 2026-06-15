import pytest
from datetime import datetime, timezone

from app.modules.reports.data.model import AcceptanceReport, ReportStatus
from app.modules.reports.domain.errors import ReportNotFoundError
from app.modules.reports.domain.usecases.download_report import DownloadReportUseCase
from app.modules.reports.domain.usecases.query_reports import (
    GetReportUseCase,
    ListMyReportsUseCase,
    ListReportsUseCase,
)
from app.modules.reports.storage import InMemoryObjectStorage
from tests.reports.fakes import FakeAcceptanceReportRepo, FakeReportSourceRepo


def _r(rid, creator, status, period="2026-06") -> AcceptanceReport:
    return AcceptanceReport(
        id=rid, period=period, creator_user_id=creator, created_by="u_admin",
        status=status, object_key=f"reports/{period}/{rid}.docx",
    )


@pytest.mark.asyncio
async def test_list_my_returns_own_final_and_amended():
    repo = FakeAcceptanceReportRepo([
        _r("rpt_1", "u_a", ReportStatus.FINAL),
        _r("rpt_2", "u_a", ReportStatus.DRAFT),
        _r("rpt_3", "u_b", ReportStatus.FINAL),
        _r("rpt_4", "u_a", ReportStatus.AMENDED),
    ])
    uc = ListMyReportsUseCase(report_repo=repo)
    out = await uc.execute(creator_user_id="u_a")
    ids = {r.id for r in out}
    assert ids == {"rpt_1", "rpt_4"}  # final + amended, not draft, not other creator


@pytest.mark.asyncio
async def test_admin_list_filters():
    repo = FakeAcceptanceReportRepo([
        _r("rpt_1", "u_a", ReportStatus.FINAL),
        _r("rpt_2", "u_b", ReportStatus.DRAFT),
    ])
    uc = ListReportsUseCase(report_repo=repo, source_repo=FakeReportSourceRepo())
    drafts = await uc.execute(period="2026-06", status=ReportStatus.DRAFT, creator_user_id=None)
    assert [r.report.id for r in drafts] == ["rpt_2"]
    assert all(rw.email is None for rw in drafts)


@pytest.mark.asyncio
async def test_get_missing_raises():
    uc = GetReportUseCase(report_repo=FakeAcceptanceReportRepo([]))
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id="nope")


@pytest.mark.asyncio
async def test_admin_download_any():
    storage = InMemoryObjectStorage()
    await storage.put("reports/2026-06/rpt_1.docx", b"BYTES", content_type="application/x")
    repo = FakeAcceptanceReportRepo([_r("rpt_1", "u_a", ReportStatus.DRAFT)])
    uc = DownloadReportUseCase(
        report_repo=repo, storage=storage,
        source_repo=FakeReportSourceRepo(emails={"u_a": "a@example.com"}),
    )
    filename, data = await uc.execute(report_id="rpt_1", require_creator_id=None)
    assert data == b"BYTES" and filename.endswith(".docx")


@pytest.mark.asyncio
async def test_creator_download_blocked_for_draft_or_other():
    storage = InMemoryObjectStorage()
    await storage.put("reports/2026-06/rpt_1.docx", b"BYTES", content_type="application/x")
    repo = FakeAcceptanceReportRepo([
        _r("rpt_1", "u_a", ReportStatus.DRAFT),
        _r("rpt_2", "u_b", ReportStatus.FINAL),
    ])
    uc = DownloadReportUseCase(
        report_repo=repo, storage=storage,
        source_repo=FakeReportSourceRepo(emails={}),
    )
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id="rpt_1", require_creator_id="u_a")
    with pytest.raises(ReportNotFoundError):
        await uc.execute(report_id="rpt_2", require_creator_id="u_a")


@pytest.mark.asyncio
async def test_creator_download_own_final_ok():
    storage = InMemoryObjectStorage()
    await storage.put("reports/2026-06/rpt_1.docx", b"OK", content_type="application/x")
    repo = FakeAcceptanceReportRepo([_r("rpt_1", "u_a", ReportStatus.FINAL)])
    uc = DownloadReportUseCase(
        report_repo=repo, storage=storage,
        source_repo=FakeReportSourceRepo(emails={}),
    )
    _, data = await uc.execute(report_id="rpt_1", require_creator_id="u_a")
    assert data == b"OK"


@pytest.mark.asyncio
async def test_download_filename_uses_email_local_part_and_period():
    # report with period 2026-06 for creator u_creator whose email is abc@example.com
    storage = InMemoryObjectStorage()
    await storage.put("reports/2026-06/rpt_1.docx", b"DATA", content_type="application/x")
    repo = FakeAcceptanceReportRepo([_r("rpt_1", "u_creator", ReportStatus.DRAFT)])
    uc = DownloadReportUseCase(
        report_repo=repo,
        storage=storage,
        source_repo=FakeReportSourceRepo(emails={"u_creator": "abc@example.com"}),
    )
    filename, _ = await uc.execute(report_id="rpt_1", require_creator_id=None)
    assert filename == "abc_report_6_2026.docx"


@pytest.mark.asyncio
async def test_download_filename_falls_back_to_creator_id_when_no_email():
    storage = InMemoryObjectStorage()
    await storage.put("reports/2026-06/rpt_1.docx", b"DATA", content_type="application/x")
    repo = FakeAcceptanceReportRepo([_r("rpt_1", "u_creator", ReportStatus.DRAFT)])
    uc = DownloadReportUseCase(
        report_repo=repo,
        storage=storage,
        source_repo=FakeReportSourceRepo(emails={}),  # no email
    )
    filename, _ = await uc.execute(report_id="rpt_1", require_creator_id=None)
    assert filename == "u_creator_report_6_2026.docx"


def _report(rid: str, creator: str, created_at: datetime) -> AcceptanceReport:
    return AcceptanceReport(
        id=rid, period="2026-06", creator_user_id=creator, created_by="u_admin",
        object_key=f"reports/2026-06/{rid}.docx", created_at=created_at,
    )


@pytest.mark.asyncio
async def test_list_reports_sorts_newest_first_and_attaches_email():
    older = _report("rpt_old", "u_a", datetime(2026, 6, 1, tzinfo=timezone.utc))
    newer = _report("rpt_new", "u_b", datetime(2026, 6, 9, tzinfo=timezone.utc))
    uc = ListReportsUseCase(
        report_repo=FakeAcceptanceReportRepo([older, newer]),
        source_repo=FakeReportSourceRepo(emails={"u_a": "a@x.com", "u_b": "b@x.com"}),
    )
    out = await uc.execute(period="2026-06", status=None, creator_user_id=None)
    assert [r.report.id for r in out] == ["rpt_new", "rpt_old"]  # newest first
    assert out[0].email == "b@x.com"
    assert out[1].email == "a@x.com"
