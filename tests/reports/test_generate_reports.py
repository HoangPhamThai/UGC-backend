import pytest

from app.modules.profiles.data.model import CreatorProfile, REQUIRED_PROFILE_FIELDS
from app.modules.reports.data.model import ReportStatus
from app.modules.reports.domain.usecases.generate_reports import GenerateReportsUseCase
from app.modules.reports.storage import InMemoryObjectStorage
from app.modules.workspaces.data.model import ArticleStatus
from tests.conftest import FakeArticleRepo, make_article
from tests.profiles.test_usecases import FakeProfileRepo
from tests.reports.fakes import FakeAcceptanceReportRepo, FakeReportSourceRepo, FakeTemplateRepo, make_eligible, RecordingEmailService

ALL_REQUIRED = {f: "x" for f in REQUIRED_PROFILE_FIELDS}


def _uc(*, eligible, articles, reports=None, captured=None, active_template=None, email_service=None):
    storage = InMemoryObjectStorage()

    def fake_render(*, scalars, line_items, template_bytes=None):
        if captured is not None:
            captured.append({"scalars": scalars, "line_items": line_items, "template_bytes": template_bytes})
        return b"DOCX-BYTES"

    return (
        GenerateReportsUseCase(
            report_repo=FakeAcceptanceReportRepo(reports or []),
            source_repo=FakeReportSourceRepo(eligible=eligible),
            profile_repo=FakeProfileRepo([CreatorProfile(user_id="u_a", **ALL_REQUIRED)]),
            article_repo=FakeArticleRepo(articles),
            storage=storage,
            render=fake_render,
            template_repo=FakeTemplateRepo(active_template),
            email_service=email_service,
        ),
        storage,
    )


@pytest.mark.asyncio
async def test_generate_creates_draft_locks_articles_and_stores_docx():
    arts = [
        make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1"),
        make_article(status=ArticleStatus.APPROVED, aid="art_2", workspace_id="ws_1"),
    ]
    uc, storage = _uc(
        eligible=[make_eligible("art_1", "u_a"), make_eligible("art_2", "u_a")],
        articles=arts,
    )
    created = await uc.execute(
        period="2026-06", article_award_price=500_000, tax_rate=0.05,
        created_by="u_admin",
    )
    assert len(created) == 1
    r = created[0]
    assert r.status == ReportStatus.DRAFT
    assert r.total_approved_articles == 2
    assert r.total_award == 1_000_000
    assert r.tax == 50_000  # round(1_000_000 * 0.05)
    assert r.final_award == 950_000
    assert r.final_award_verbal
    assert await storage.get(r.object_key) == b"DOCX-BYTES"
    assert all(a.report_id == r.id for a in arts)


@pytest.mark.asyncio
async def test_generate_skips_creator_with_existing_period_report():
    from app.modules.reports.data.model import AcceptanceReport
    existing = AcceptanceReport(
        period="2026-06", creator_user_id="u_a", created_by="u_admin",
        object_key="reports/2026-06/old.docx",
    )
    uc, _ = _uc(
        eligible=[make_eligible("art_1", "u_a")],
        articles=[make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")],
        reports=[existing],
    )
    created = await uc.execute(
        period="2026-06", article_award_price=1, tax_rate=0.0, created_by="u_admin",
    )
    assert created == []


@pytest.mark.asyncio
async def test_generate_single_creator_filter():
    arts = [
        make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1"),
        make_article(status=ArticleStatus.APPROVED, aid="art_3", workspace_id="ws_2"),
    ]
    uc, _ = _uc(
        eligible=[make_eligible("art_1", "u_a"), make_eligible("art_3", "u_b")],
        articles=arts,
    )
    created = await uc.execute(
        period="2026-06", article_award_price=100, tax_rate=0.0,
        created_by="u_admin", creator_user_id="u_a",
    )
    assert len(created) == 1 and created[0].creator_user_id == "u_a"


@pytest.mark.asyncio
async def test_generate_passes_active_template_bytes_to_render():
    captured: list[dict] = []
    uc, _ = _uc(
        eligible=[make_eligible("art_1", "u_a")],
        articles=[make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")],
        captured=captured,
        active_template=b"ACTIVE-TPL",
    )
    await uc.execute(period="2026-06", article_award_price=1, tax_rate=0.0, created_by="u_admin")
    assert captured and captured[0]["template_bytes"] == b"ACTIVE-TPL"


@pytest.mark.asyncio
async def test_generate_schedules_created_email_per_report():
    from app.modules.email.messages import ReportEmailEvent
    email = RecordingEmailService()
    uc, _ = _uc(
        eligible=[make_eligible("art_1", "u_a")],
        articles=[make_article(status=ArticleStatus.APPROVED, aid="art_1", workspace_id="ws_1")],
        email_service=email,
    )
    created = await uc.execute(
        period="2026-06", article_award_price=500_000, tax_rate=0.05, created_by="u_admin",
    )
    assert len(created) == 1
    assert email.report_events == [(ReportEmailEvent.CREATED, "2026-06", "u_a")]
