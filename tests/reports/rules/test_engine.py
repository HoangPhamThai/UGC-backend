from app.modules.reports.rules.engine import apply_rules
from app.modules.reports.rules.ir import RuleIR

BONUS = {
    "id": "bonus", "description": "", "target": "article_bonus_money",
    "scope": "line_item", "type": "lookup_table",
    "inputs": ["article_platform", "article_view"],
    "match": [
        {"when": {"article_platform": "Threads", "article_view": [5000, 10000]}, "value": 25000},
        {"when": {"article_platform": "Tiktok", "article_view": [10000, 20000]}, "value": 25000},
    ],
    "default": 0,
}
TAX = {
    "id": "tax", "description": "", "target": "tax", "scope": "scalar",
    "type": "conditional_formula", "inputs": ["total_award"],
    "cases": [{"when": "total_award > 2000000", "value": "round(total_award * 0.10)"}],
    "default": "keep",
}


def _ir(*rules):
    return RuleIR.model_validate({"version": 1, "rules": list(rules)})


def test_scalar_override_applies_when_case_matches():
    scalars = {"total_award": 3_000_000, "tax": 0}
    out_s, _ = apply_rules(_ir(TAX), scalars, [])
    assert out_s["tax"] == 300_000


def test_scalar_keeps_base_when_no_case():
    scalars = {"total_award": 1_000_000, "tax": 42}
    out_s, _ = apply_rules(_ir(TAX), scalars, [])
    assert out_s["tax"] == 42  # default "keep"


def test_line_item_lookup_override():
    items = [
        {"article_platform": "Threads", "article_view": 6000, "article_bonus_money": 0},
        {"article_platform": "Tiktok", "article_view": 15000, "article_bonus_money": 0},
        {"article_platform": "Threads", "article_view": 999, "article_bonus_money": 0},
    ]
    _, out = apply_rules(_ir(BONUS), {}, items)
    assert out[0]["article_bonus_money"] == 25000
    assert out[1]["article_bonus_money"] == 25000
    assert out[2]["article_bonus_money"] == 0  # no match -> default


def test_no_rules_passthrough():
    scalars = {"tax": 7}
    out_s, out_i = apply_rules(_ir(), scalars, [{"x": 1}])
    assert out_s == {"tax": 7} and out_i == [{"x": 1}]


def test_runtime_error_keeps_base(monkeypatch):
    bad = dict(TAX, cases=[{"when": "total_award > 0", "value": "total_award / 0"}])
    out_s, _ = apply_rules(_ir(bad), {"total_award": 10, "tax": 5}, [])
    assert out_s["tax"] == 5  # division error -> keep base
