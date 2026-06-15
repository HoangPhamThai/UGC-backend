from datetime import datetime, timezone

from app.modules.reports.data.model import AcceptanceReport, LineItem
from app.modules.reports.helpers import DOCX_MIME, period_bounds, report_to_render_inputs


def test_period_bounds_june():
    start, end = period_bounds("2026-06")
    assert start == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert end.year == 2026 and end.month == 6 and end.day == 30
    assert end > start


def test_period_bounds_december_wraps_year():
    start, end = period_bounds("2026-12")
    assert start.month == 12 and start.day == 1
    assert end.month == 12 and end.day == 31


def _report() -> AcceptanceReport:
    return AcceptanceReport(
        id="rpt_1",
        period="2026-06",
        creator_user_id="u_creator",
        created_by="u_admin",
        created_at=datetime(2026, 6, 14, tzinfo=timezone.utc),
        creator_snapshot={
            "full_name": "Nguyen Van A",
            "primary_address": "Addr 1",
            "current_address": "",
            "bank_name": "ACB",
            "bank_branch": "HCM",
        },
        line_items=[
            LineItem(article_id="art_1", seq=1, platform="tiktok",
                     on_air_date="2026-06-01", link="https://x", views=100),
        ],
        article_award_price=500_000,
        total_approved_articles=1,
        total_award=500_000,
        tax=50_000,
        final_award=450_000,
        final_award_verbal="Bốn trăm năm mươi nghìn",
        object_key="reports/2026-06/rpt_1.docx",
    )


def test_render_inputs_map_snapshot_and_financials():
    scalars, items = report_to_render_inputs(_report())
    assert scalars["creator_name"] == "Nguyen Van A"
    assert scalars["creator_bank"] == "ACB"
    assert scalars["creator_bank_branch"] == "HCM"  # fixed typo token
    assert scalars["creator_current_address"] == "Addr 1"  # falls back to primary when blank
    assert scalars["final_award_verbal"] == "Bốn trăm năm mươi nghìn"
    assert scalars["total_award"] == "500.000"  # VN dot thousands
    assert scalars["created_at"] == "14/06/2026"
    assert len(items) == 1
    assert items[0]["article_id_autoinc"] == "1"
    assert items[0]["article_platform"] == "tiktok"
    assert items[0]["article_view"] == "100"


def test_docx_mime_constant():
    assert DOCX_MIME.endswith("wordprocessingml.document")


def _report_with_dates(dob: str, doi: str) -> AcceptanceReport:
    r = _report()
    r.creator_snapshot = {**r.creator_snapshot, "date_of_birth": dob, "social_id_date_of_issue": doi}
    return r


def test_render_inputs_format_dob_and_issue_date_as_dmy():
    scalars, _ = report_to_render_inputs(_report_with_dates("1990-01-15", "2015-03-02"))
    assert scalars["creator_date_of_birth"] == "15/01/1990"
    assert scalars["creator_social_id_date_of_issue"] == "02/03/2015"


def test_render_inputs_pass_through_unparseable_or_empty_dates():
    scalars, _ = report_to_render_inputs(_report_with_dates("", "15/03/2015"))
    assert scalars["creator_date_of_birth"] == ""          # empty stays empty
    assert scalars["creator_social_id_date_of_issue"] == "15/03/2015"  # already-dmy / non-ISO passes through


def test_render_inputs_total_articles_equals_approved_count():
    scalars, _ = report_to_render_inputs(_report())
    # total_articles = số bài đã duyệt dùng để tạo báo cáo (bằng total_approved_articles)
    assert scalars["total_articles"] == "1"
    assert scalars["total_articles"] == scalars["total_approved_articles"]


from app.modules.reports.helpers import report_to_render_inputs


def test_bank_branch_key_has_correct_spelling():
    from tests.reports.test_model import _report
    scalars, _ = report_to_render_inputs(_report())
    assert "creator_bank_branch" in scalars
    assert "creatir_bank_branch" not in scalars


def test_line_items_include_article_id_for_image_lookup():
    from tests.reports.test_model import _report
    _, items = report_to_render_inputs(_report())
    assert "article_id" in items[0]
    assert items[0]["article_id"] == "art_1"


def test_line_items_include_article_image_empty_when_none():
    from tests.reports.test_model import _report
    _, items = report_to_render_inputs(_report())
    assert items[0]["article_image"] == ""


def test_line_items_include_article_image_key_when_set():
    from tests.reports.test_model import _report
    from app.modules.reports.data.model import LineItem
    li = LineItem(
        article_id="art_1", seq=1, on_air_date="2026-06-01",
        article_image="reports/2026-06/rpt_1/images/art_1.jpg",
    )
    _, items = report_to_render_inputs(_report(line_items=[li]))
    assert items[0]["article_image"] == "reports/2026-06/rpt_1/images/art_1.jpg"


def test_line_items_include_article_bonus_money():
    from tests.reports.test_model import _report
    _, items = report_to_render_inputs(_report())
    assert items[0]["article_bonus_money"] == "  "
