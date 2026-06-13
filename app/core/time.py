# app/core/time.py
"""Business-time helpers.

On-air dates are calendar days, and "today"/"not in the past" must be judged in
the business timezone (Asia/Ho_Chi_Minh), not UTC, so a creator near midnight
local time sees a consistent "earliest = today". See article.md §3.2/§7.
"""
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def business_today() -> date:
    """Current calendar date in the business timezone."""
    return datetime.now(BUSINESS_TZ).date()


def date_to_storage(d: date) -> datetime:
    """Encode a calendar date for MongoDB.

    bson cannot store a bare `date`; we store midnight UTC. Reading the value
    back yields the same calendar date (Pydantic coerces the midnight datetime
    to `date`).
    """
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def business_day_start_utc(d: date) -> datetime:
    """Inclusive start of calendar day `d` (00:00 in the business tz) as an
    aware UTC datetime. Used to lower-bound a `created_at` window filter."""
    return datetime.combine(d, time.min, tzinfo=BUSINESS_TZ).astimezone(timezone.utc)


def business_day_end_utc(d: date) -> datetime:
    """Inclusive end of calendar day `d` (23:59:59.999999 in the business tz)
    as an aware UTC datetime. Used to upper-bound a `created_at` window filter."""
    return datetime.combine(d, time.max, tzinfo=BUSINESS_TZ).astimezone(timezone.utc)
