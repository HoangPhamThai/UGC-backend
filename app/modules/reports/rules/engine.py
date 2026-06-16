"""Apply a validated rule IR over base scalar + line-item values, overriding only
the fields each rule targets. Pure numeric in/out — formatting (e.g. _vnd) is the
caller's job. Runtime errors in a single rule keep that field's base value."""
import logging
from typing import Any

from app.modules.reports.rules.expr import ExprError, eval_expr
from app.modules.reports.rules.ir import Rule, RuleIR
from app.modules.reports.rules.registry import field_keys_in_scope

logger = logging.getLogger("reports.rules.engine")


def apply_rules(
    ir: RuleIR, scalars: dict[str, Any], line_items: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    out_scalars = dict(scalars)
    out_items = [dict(it) for it in line_items]
    for rule in ir.rules:
        try:
            if rule.scope == "scalar":
                _apply_scalar(rule, out_scalars)
            else:
                for item in out_items:
                    _apply_line_item(rule, item, out_scalars)
        except Exception as exc:  # noqa: BLE001 — one rule must not crash generation
            logger.warning("rule %s failed, keeping base: %s", rule.id, exc)
    return out_scalars, out_items


def _namespace(rule: Rule, item: dict | None, scalars: dict) -> dict[str, Any]:
    keys = field_keys_in_scope(rule.scope)
    ns: dict[str, Any] = {}
    for k in keys:
        if k in scalars:
            ns[k] = scalars[k]
    if item is not None:
        for k in keys:
            if k in item:
                ns[k] = item[k]
    return ns


def _apply_scalar(rule: Rule, scalars: dict) -> None:
    ns = _namespace(rule, None, scalars)
    val = _compute(rule, ns)
    if val is not None:
        scalars[rule.target] = int(round(val))


def _apply_line_item(rule: Rule, item: dict, scalars: dict) -> None:
    ns = _namespace(rule, item, scalars)
    val = _compute(rule, ns)
    if val is not None:
        item[rule.target] = int(round(val))


def _compute(rule: Rule, ns: dict[str, Any]):
    """Return the new numeric value, or None to keep the base value."""
    if rule.type == "lookup_table":
        for row in rule.match or []:
            if _row_matches(row.when, ns):
                return row.value
        return rule.default if isinstance(rule.default, int) else None
    # conditional_formula
    for case in rule.cases or []:
        if _truthy(eval_expr(case.when, ns)):
            return eval_expr(case.value, ns)
    if rule.default in (None, "keep"):
        return None
    return eval_expr(rule.default, ns)  # default is an expression string


def _row_matches(when: dict, ns: dict[str, Any]) -> bool:
    for key, cond in when.items():
        if key not in ns:
            return False
        actual = ns[key]
        if isinstance(cond, list):  # inclusive [lo, hi]
            if actual is None or not (cond[0] <= actual <= cond[1]):
                return False
        else:  # enum/string, case-insensitive
            if str(actual).strip().lower() != str(cond).strip().lower():
                return False
    return True


def _truthy(v) -> bool:
    return bool(v)
