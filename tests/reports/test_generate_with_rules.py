from app.modules.reports.rules.engine import apply_rules
from app.modules.reports.rules.ir import RuleIR
from app.modules.reports.helpers import _vnd


def test_apply_rules_produces_expected_numeric_overrides():
    ir = RuleIR.model_validate({"version": 1, "rules": [
        {"id": "tax", "description": "", "target": "tax", "scope": "scalar",
         "type": "conditional_formula", "inputs": ["total_award"],
         "cases": [{"when": "total_award > 2000000", "value": "round(total_award * 0.10)"}],
         "default": "keep"},
        {"id": "bonus", "description": "", "target": "article_bonus_money", "scope": "line_item",
         "type": "lookup_table", "inputs": ["article_platform", "article_view"],
         "match": [{"when": {"article_platform": "Threads", "article_view": [5000, 10000]}, "value": 25000}],
         "default": 0},
    ]})
    scalars = {"total_award": 3_000_000, "tax": 0, "final_award": 3_000_000}
    items = [{"article_platform": "Threads", "article_view": 6000, "article_bonus_money": 0}]
    out_s, out_i = apply_rules(ir, scalars, items)
    assert out_s["tax"] == 300_000
    assert _vnd(out_i[0]["article_bonus_money"]) == "25.000"
