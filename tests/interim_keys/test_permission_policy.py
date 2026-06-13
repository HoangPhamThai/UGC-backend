from app.core.permissions import Permission, interim_key_allows, INTERIM_ALLOWED_PERMISSIONS


def test_stats_read_is_allowed_for_interim():
    assert Permission.STATS_READ in INTERIM_ALLOWED_PERMISSIONS
    assert interim_key_allows([Permission.STATS_READ]) is True


def test_mutation_permission_is_blocked():
    assert interim_key_allows([Permission.USERS_CREATE_QC]) is False


def test_mixed_set_is_blocked_if_any_disallowed():
    assert interim_key_allows([Permission.STATS_READ, Permission.USERS_CREATE_QC]) is False


def test_empty_needed_is_allowed():
    assert interim_key_allows([]) is True
