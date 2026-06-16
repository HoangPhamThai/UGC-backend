import pytest

from app.modules.reports.rules.expr import ExprError, eval_expr, validate_expr


def test_eval_arithmetic_and_funcs():
    ns = {"total_award": 3_000_000}
    assert eval_expr("round(total_award * 0.10)", ns) == 300_000
    assert eval_expr("min(total_award, 1000)", ns) == 1000


def test_eval_comparison_and_logic():
    ns = {"total_award": 3_000_000}
    assert eval_expr("total_award > 2000000", ns) is True
    assert eval_expr("total_award > 2000000 and total_award < 5000000", ns) is True


def test_validate_rejects_unknown_name():
    with pytest.raises(ExprError):
        validate_expr("foo + 1", {"total_award"})


def test_validate_rejects_attribute_and_call():
    with pytest.raises(ExprError):
        validate_expr("total_award.__class__", {"total_award"})
    with pytest.raises(ExprError):
        validate_expr("open('x')", {"total_award"})
    with pytest.raises(ExprError):
        validate_expr("data[0]", {"data"})


def test_validate_accepts_whitelisted():
    validate_expr("round(total_award * 0.1) if total_award > 0 else 0", {"total_award"})
    validate_expr("max(a, b) + min(a, b)", {"a", "b"})
