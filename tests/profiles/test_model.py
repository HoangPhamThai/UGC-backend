from app.modules.profiles.data.model import CreatorProfile, REQUIRED_PROFILE_FIELDS

ALL_REQUIRED = {f: "x" for f in REQUIRED_PROFILE_FIELDS}


def test_blank_profile_is_incomplete():
    p = CreatorProfile(user_id="u_1")
    assert p.is_complete is False


def test_profile_with_all_required_fields_is_complete():
    p = CreatorProfile(user_id="u_1", **ALL_REQUIRED)
    assert p.is_complete is True


def test_current_address_is_not_required():
    fields = dict(ALL_REQUIRED)  # current_address intentionally omitted
    p = CreatorProfile(user_id="u_1", **fields)
    assert "current_address" not in REQUIRED_PROFILE_FIELDS
    assert p.is_complete is True


def test_whitespace_only_field_does_not_count_as_complete():
    fields = dict(ALL_REQUIRED, full_name="   ")
    p = CreatorProfile(user_id="u_1", **fields)
    assert p.is_complete is False
