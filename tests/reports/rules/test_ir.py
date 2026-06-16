from app.modules.reports.rules.ir import RuleIR


def test_parse_lookup_and_conditional():
    raw = {
        "version": 1,
        "rules": [
            {
                "id": "bonus_by_views", "description": "x",
                "target": "article_bonus_money", "scope": "line_item",
                "type": "lookup_table", "inputs": ["article_platform", "article_view"],
                "match": [
                    {"when": {"article_platform": "Threads", "article_view": [5000, 10000]}, "value": 25000},
                ],
                "default": 0,
            },
            {
                "id": "pit_tax", "description": "y",
                "target": "tax", "scope": "scalar",
                "type": "conditional_formula", "inputs": ["total_award"],
                "cases": [{"when": "total_award > 2000000", "value": "round(total_award * 0.10)"}],
                "default": "keep",
            },
        ],
    }
    ir = RuleIR.model_validate(raw)
    assert ir.rules[0].type == "lookup_table"
    assert ir.rules[0].match[0].value == 25000
    assert ir.rules[1].cases[0].when == "total_award > 2000000"
    assert ir.rules[1].default == "keep"


def test_empty_rules_ok():
    ir = RuleIR.model_validate({"version": 1, "rules": []})
    assert ir.rules == []
