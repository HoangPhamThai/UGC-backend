from app.modules.reports.rules.validator import validate_ir

_OK = {
    "version": 1,
    "rules": [
        {"id": "bonus", "description": "", "target": "article_bonus_money",
         "scope": "line_item", "type": "lookup_table",
         "inputs": ["article_platform", "article_view"],
         "match": [{"when": {"article_platform": "Threads", "article_view": [5000, 10000]}, "value": 25000}],
         "default": 0},
        {"id": "tax", "description": "", "target": "tax", "scope": "scalar",
         "type": "conditional_formula", "inputs": ["total_award"],
         "cases": [{"when": "total_award > 2000000", "value": "round(total_award * 0.10)"}],
         "default": "keep"},
    ],
}


def test_valid_ir_has_no_errors():
    assert validate_ir(_OK) == []


def test_bad_shape_reports_error():
    errs = validate_ir({"rules": [{"id": "x"}]})
    assert errs  # missing required fields


def test_unknown_target():
    ir = {"version": 1, "rules": [dict(_OK["rules"][1], target="nope")]}
    assert any("nope" in e for e in validate_ir(ir))


def test_non_writable_target():
    ir = {"version": 1, "rules": [dict(_OK["rules"][1], target="article_view", scope="line_item")]}
    assert any("article_view" in e for e in validate_ir(ir))


def test_scope_mismatch_target():
    ir = {"version": 1, "rules": [dict(_OK["rules"][1], scope="line_item")]}
    assert any("scope" in e.lower() for e in validate_ir(ir))


def test_scalar_rule_cannot_read_line_item_field():
    bad = dict(_OK["rules"][1], inputs=["article_view"],
               cases=[{"when": "article_view > 1", "value": "0"}])
    assert any("article_view" in e for e in validate_ir({"version": 1, "rules": [bad]}))


def test_bad_expression_rejected():
    bad = dict(_OK["rules"][1], cases=[{"when": "__import__('os')", "value": "0"}])
    assert validate_ir({"version": 1, "rules": [bad]})


def test_duplicate_ids():
    ir = {"version": 1, "rules": [_OK["rules"][1], _OK["rules"][1]]}
    assert any("trùng" in e.lower() or "duplicate" in e.lower() for e in validate_ir(ir))


def test_lookup_range_lo_gt_hi():
    bad = dict(_OK["rules"][0])
    bad = {**bad, "match": [{"when": {"article_platform": "Threads", "article_view": [10, 5]}, "value": 1}]}
    assert validate_ir({"version": 1, "rules": [bad]})


def test_lookup_enum_value_is_case_insensitive():
    bad = dict(_OK["rules"][0])
    bad = {**bad, "match": [{"when": {"article_platform": "tiktok", "article_view": [1, 2]}, "value": 1}]}
    # lowercase 'tiktok' must be accepted (engine matches case-insensitively)
    assert validate_ir({"version": 1, "rules": [bad]}) == []
