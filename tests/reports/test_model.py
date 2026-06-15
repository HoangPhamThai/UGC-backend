from app.modules.reports.data.model import AcceptanceReport, LineItem, ReportStatus


def _report(**over) -> AcceptanceReport:
    base = dict(
        period="2026-06",
        creator_user_id="u_creator",
        created_by="u_admin",
        creator_snapshot={"full_name": "Nguyen Van A"},
        line_items=[
            LineItem(
                article_id="art_1", seq=1, platform="tiktok",
                on_air_date="2026-06-01", link="https://x", views=100,
            )
        ],
        article_award_price=500_000,
        total_approved_articles=1,
        total_award=500_000,
        tax=50_000,
        final_award=450_000,
        final_award_verbal="Bốn trăm năm mươi nghìn",
        object_key="reports/2026-06/rpt_1.docx",
    )
    base.update(over)
    return AcceptanceReport(**base)


def test_defaults_to_draft_and_prefixed_id():
    r = _report()
    assert r.status == ReportStatus.DRAFT
    assert r.id.startswith("rpt_")
    assert r.finalized_at is None


def test_status_values():
    assert ReportStatus.DRAFT.value == "draft"
    assert ReportStatus.FINAL.value == "final"


def test_line_item_carries_seq_and_views():
    r = _report()
    assert r.line_items[0].seq == 1
    assert r.line_items[0].views == 100


def test_report_status_has_amended():
    from app.modules.reports.data.model import ReportStatus
    assert ReportStatus.AMENDED.value == "amended"


def test_reviewing_status_value():
    assert ReportStatus.REVIEWING.value == "reviewing"


def test_line_item_new_field_defaults():
    li = LineItem(article_id="art_1", seq=1, on_air_date="2026-06-01")
    assert li.article_image is None
    assert li.article_bonus_money == "  "


def test_line_item_accepts_article_image():
    li = LineItem(
        article_id="art_1", seq=1, on_air_date="2026-06-01",
        article_image="reports/2026-06/rpt_1/images/art_1.jpg",
    )
    assert li.article_image == "reports/2026-06/rpt_1/images/art_1.jpg"
