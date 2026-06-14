# app/modules/reports/helpers.py
import calendar
from datetime import datetime, timezone

from app.modules.reports.data.model import AcceptanceReport

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def period_bounds(period: str) -> tuple[datetime, datetime]:
    """'YYYY-MM' -> (first-day 00:00 UTC, last-day 23:59:59 UTC). The articles
    collection stores on_air_date as midnight-UTC, so these bounds bracket the
    whole month inclusively."""
    year_s, month_s = period.split("-")
    year, month = int(year_s), int(month_s)
    last_day = calendar.monthrange(year, month)[1]
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _vnd(n: int) -> str:
    """Format an integer with Vietnamese dot thousands separators (1000 -> '1.000')."""
    return f"{n:,}".replace(",", ".")


def report_to_render_inputs(report: AcceptanceReport) -> tuple[dict, list[dict]]:
    """Map the report model to the template's scalar tokens + Điều 2 row dicts.
    Keys are the EXACT template token names (incl. the `creatir_bank_branch`
    typo). current_address falls back to primary_address when blank."""
    s = report.creator_snapshot
    primary = s.get("primary_address", "") or ""
    scalars = {
        "created_at": report.created_at.strftime("%d/%m/%Y"),
        "creator_name": s.get("full_name", "") or "",
        "creator_date_of_birth": s.get("date_of_birth", "") or "",
        "creator_social_id": s.get("social_id", "") or "",
        "creator_social_id_date_of_issue": s.get("social_id_date_of_issue", "") or "",
        "creator_social_id_place_of_issue": s.get("social_id_place_of_issue", "") or "",
        "creator_primary_address": primary,
        "creator_current_address": (s.get("current_address") or primary),
        "creator_tax_number": s.get("tax_number", "") or "",
        "creator_bank_account_number": s.get("bank_account_number", "") or "",
        "creator_bank": s.get("bank_name", "") or "",
        "creatir_bank_branch": s.get("bank_branch", "") or "",
        "total_approved_articles": str(report.total_approved_articles),
        "article_award_price": _vnd(report.article_award_price),
        "total_award": _vnd(report.total_award),
        "tax": _vnd(report.tax),
        "final_award": _vnd(report.final_award),
        "final_award_verbal": report.final_award_verbal,
    }
    line_items = [
        {
            "article_platform": li.platform or "",
            "article_id_autoinc": str(li.seq),
            "article_on_air": li.on_air_date,
            "article_link": li.link or "",
            "article_view": "" if li.views is None else str(li.views),
        }
        for li in report.line_items
    ]
    return scalars, line_items
