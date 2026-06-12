from datetime import datetime, timezone, timedelta

from app.core.model import to_epoch_ms


def test_naive_datetime_treated_as_utc():
    # Mongo (without tz_aware) returns naive UTC. A naive value must be read as UTC,
    # NOT as the server's local time.
    naive = datetime(2026, 6, 12, 3, 0, 0)
    aware = datetime(2026, 6, 12, 3, 0, 0, tzinfo=timezone.utc)
    assert to_epoch_ms(naive) == to_epoch_ms(aware)


def test_known_utc_value():
    # 2021-01-01T00:00:00Z == 1609459200000 ms
    dt = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert to_epoch_ms(dt) == 1609459200000


def test_aware_non_utc_offset_is_respected():
    # An aware datetime in +07:00 is the same instant as 00:00Z the same day... minus 7h.
    plus7 = timezone(timedelta(hours=7))
    dt = datetime(2021, 1, 1, 7, 0, 0, tzinfo=plus7)  # == 2021-01-01T00:00:00Z
    assert to_epoch_ms(dt) == 1609459200000
