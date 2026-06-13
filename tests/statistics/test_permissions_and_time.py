from datetime import date, datetime, timezone

from app.core.permissions import Permission, has_permission
from app.core.time import business_day_start_utc, business_day_end_utc
from app.modules.users.data.model import UserRole
from tests.conftest import make_user


def test_admin_has_stats_read():
    admin = make_user(role=UserRole.ADMIN, uid="u_admin")
    assert has_permission(admin, Permission.STATS_READ) is True


def test_superuser_has_stats_read():
    su = make_user(role=UserRole.SUPERUSER, uid="u_su")
    assert has_permission(su, Permission.STATS_READ) is True


def test_qc_and_creator_lack_stats_read():
    qc = make_user(role=UserRole.QC, uid="u_qc")
    creator = make_user(role=UserRole.CREATOR, uid="u_creator")
    assert has_permission(qc, Permission.STATS_READ) is False
    assert has_permission(creator, Permission.STATS_READ) is False


def test_business_day_start_utc_converts_ict_midnight_to_utc():
    # Asia/Ho_Chi_Minh is UTC+7 (no DST). 2026-06-13 00:00 ICT == 2026-06-12 17:00 UTC.
    start = business_day_start_utc(date(2026, 6, 13))
    assert start == datetime(2026, 6, 12, 17, 0, 0, tzinfo=timezone.utc)


def test_business_day_end_utc_is_after_start_and_same_utc_day_offset():
    # End of 2026-06-13 ICT == 2026-06-13 16:59:59.999999 UTC.
    end = business_day_end_utc(date(2026, 6, 13))
    assert end.tzinfo is not None
    assert end == datetime(2026, 6, 13, 16, 59, 59, 999999, tzinfo=timezone.utc)
    assert end > business_day_start_utc(date(2026, 6, 13))
