from app.modules.reports.rules.registry import (
    FIELD_REGISTRY, get_field, writable_keys, field_keys_in_scope,
)


def test_known_writable_and_input_fields():
    assert get_field("tax").writable is True
    assert get_field("tax").scope == "scalar"
    assert get_field("article_bonus_money").scope == "line_item"
    assert get_field("article_view").writable is False
    assert get_field("nope") is None


def test_writable_keys_contains_targets():
    ks = writable_keys()
    assert {"tax", "total_award", "final_award", "article_bonus_money"} <= ks
    assert "article_view" not in ks


def test_scope_visibility():
    # a line_item rule can read line_item + scalar fields
    li = field_keys_in_scope("line_item")
    assert "article_view" in li and "total_award" in li
    # a scalar rule can read only scalar fields
    sc = field_keys_in_scope("scalar")
    assert "total_award" in sc and "article_view" not in sc


def test_enum_field_values():
    assert get_field("article_platform").type == "enum"
    assert get_field("article_platform").enum_values is not None
    assert "Threads" in get_field("article_platform").enum_values
