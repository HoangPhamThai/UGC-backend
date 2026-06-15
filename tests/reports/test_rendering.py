from io import BytesIO
from pathlib import Path

import pytest

docx = pytest.importorskip("docx")  # skip if python-docx not installed locally

from app.modules.reports.rendering import TEMPLATE_PATH, render_acceptance_report, validate_template_bytes
from app.modules.reports.domain.errors import ReportValidationError


def _all_text(document) -> str:
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def _scalars() -> dict:
    return {
        "created_at": "14/06/2026",
        "creator_name": "Nguyen Van A",
        "creator_date_of_birth": "1990-01-15",
        "creator_social_id": "0123",
        "creator_social_id_date_of_issue": "2015-01-01",
        "creator_social_id_place_of_issue": "HCMC",
        "creator_primary_address": "Addr 1",
        "creator_current_address": "Addr 2",
        "creator_tax_number": "TAX1",
        "creator_bank_account_number": "ACC1",
        "creator_bank": "Bank",
        "creator_bank_branch": "Branch",
        "total_approved_articles": "2",
        "total_articles": "2",
        "article_award_price": "500000",
        "total_award": "1000000",
        "tax": "100000",
        "final_award": "900000",
        "final_award_verbal": "Chín trăm nghìn",
    }


def _items() -> list[dict]:
    return [
        {
            "article_id": "art_1",
            "article_platform": "tiktok", "article_id_autoinc": "1",
            "article_on_air": "2026-06-01", "article_link": "https://tt/1",
            "article_view": "100", "article_image": "", "article_bonus_money": "  ",
        },
        {
            "article_id": "art_2",
            "article_platform": "threads", "article_id_autoinc": "2",
            "article_on_air": "2026-06-02", "article_link": "https://th/2",
            "article_view": "200", "article_image": "", "article_bonus_money": "  ",
        },
    ]


def test_template_exists():
    assert Path(TEMPLATE_PATH).exists()


def test_render_substitutes_scalars_and_clones_rows():
    out = render_acceptance_report(scalars=_scalars(), line_items=_items())
    document = docx.Document(BytesIO(out))
    text = _all_text(document)

    assert "{" not in text and "}" not in text
    assert "Nguyen Van A" in text
    assert "Chín trăm nghìn" in text
    assert "https://tt/1" in text and "https://th/2" in text
    assert "tiktok" in text and "threads" in text


def test_render_handles_single_item():
    out = render_acceptance_report(scalars=_scalars(), line_items=_items()[:1])
    document = docx.Document(BytesIO(out))
    text = _all_text(document)
    assert "https://tt/1" in text and "https://th/2" not in text
    assert "{article_platform}" not in text


def test_validate_template_accepts_the_vendored_default():
    data = Path(TEMPLATE_PATH).read_bytes()
    validate_template_bytes(data)  # must not raise


def test_validate_template_rejects_non_docx():
    with pytest.raises(ReportValidationError):
        validate_template_bytes(b"not a docx")


def test_render_uses_provided_template_bytes():
    data = Path(TEMPLATE_PATH).read_bytes()
    out = render_acceptance_report(scalars=_scalars(), line_items=_items(), template_bytes=data)
    document = docx.Document(BytesIO(out))
    text = _all_text(document)
    assert "Nguyen Van A" in text and "{" not in text
