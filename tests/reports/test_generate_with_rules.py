from app.modules.reports.rules.engine import apply_rules
from app.modules.reports.rules.ir import RuleIR
from app.modules.reports.helpers import _vnd


def test_award_price_override_does_not_leak_base_between_creators():
    # Simulates the generate loop: base total_award must derive from the ORIGINAL
    # award price each iteration, even if a rule overrides article_award_price.
    ir = RuleIR.model_validate({"version": 1, "rules": [
        {"id": "price", "description": "", "target": "article_award_price", "scope": "scalar",
         "type": "conditional_formula", "inputs": ["article_award_price"],
         "cases": [{"when": "article_award_price > 0", "value": "article_award_price * 2"}],
         "default": "keep"},
    ]})
    article_award_price = 1000  # the would-be parameter
    results = []
    for count in (2, 3):  # two creators
        total_award = article_award_price * count  # base uses ORIGINAL each time
        out_s, _ = apply_rules(ir, {"tax": 0, "total_award": total_award,
                                    "final_award": total_award,
                                    "article_award_price": article_award_price}, [])
        report_award_price = int(out_s["article_award_price"])  # local, no rebind of param
        results.append((total_award, report_award_price))
    # creator 2's base total must be 1000*3, NOT contaminated to 2000*3
    assert results[0] == (2000, 2000)
    assert results[1] == (3000, 2000)


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
