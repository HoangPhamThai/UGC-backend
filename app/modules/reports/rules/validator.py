"""Semantic validation of a rule IR dict. Returns a list of human-readable
(Vietnamese) error strings; empty list means valid. Used both when the agents
service writes analysis results back and when the admin saves edited IR."""
from typing import Any

from pydantic import ValidationError

from app.modules.reports.rules.expr import ExprError, validate_expr
from app.modules.reports.rules.ir import RuleIR
from app.modules.reports.rules.registry import (
    field_keys_in_scope, get_field, writable_keys,
)


def validate_ir(ir_dict: Any) -> list[str]:
    try:
        ir = RuleIR.model_validate(ir_dict)
    except ValidationError as e:
        return [f"IR sai cấu trúc: {err['loc']} {err['msg']}" for err in e.errors()]

    errors: list[str] = []
    seen_ids: set[str] = set()
    for rule in ir.rules:
        rid = rule.id or "(no-id)"
        if rule.id in seen_ids:
            errors.append(f"Rule id trùng: {rule.id}")
        seen_ids.add(rule.id)

        target = get_field(rule.target)
        if target is None:
            errors.append(f"[{rid}] target không tồn tại: {rule.target}")
            continue
        if rule.target not in writable_keys():
            errors.append(f"[{rid}] target không được phép ghi: {rule.target}")
        if target.scope != rule.scope:
            errors.append(f"[{rid}] scope sai: target {rule.target} là {target.scope}, rule khai {rule.scope}")

        readable = field_keys_in_scope(rule.scope)
        for inp in rule.inputs:
            if get_field(inp) is None:
                errors.append(f"[{rid}] input không tồn tại: {inp}")
            elif inp not in readable:
                errors.append(f"[{rid}] input {inp} không đọc được trong scope {rule.scope}")

        if rule.type == "lookup_table":
            errors += _validate_lookup(rid, rule, readable)
        else:
            errors += _validate_conditional(rid, rule, readable)
    return errors


def _validate_lookup(rid: str, rule, readable: set[str]) -> list[str]:
    errs: list[str] = []
    if not rule.match:
        errs.append(f"[{rid}] lookup_table thiếu match")
        return errs
    inputs = set(rule.inputs)
    for i, row in enumerate(rule.match):
        for key, val in row.when.items():
            if key not in inputs:
                errs.append(f"[{rid}] match#{i}: field {key} không nằm trong inputs")
            fd = get_field(key)
            if fd is None or key not in readable:
                errs.append(f"[{rid}] match#{i}: field {key} không hợp lệ")
                continue
            if isinstance(val, list):
                if len(val) != 2 or val[0] > val[1]:
                    errs.append(f"[{rid}] match#{i}: range {val} phải là [lo, hi] với lo<=hi")
            elif fd.type == "enum" and fd.enum_values and str(val) not in fd.enum_values:
                errs.append(f"[{rid}] match#{i}: giá trị enum {val!r} ngoài {fd.enum_values}")
    if not isinstance(rule.default, int):
        errs.append(f"[{rid}] lookup_table default phải là số nguyên")
    return errs


def _validate_conditional(rid: str, rule, readable: set[str]) -> list[str]:
    errs: list[str] = []
    if not rule.cases:
        errs.append(f"[{rid}] conditional_formula thiếu cases")
        return errs
    for i, case in enumerate(rule.cases):
        for label, expr in (("when", case.when), ("value", case.value)):
            try:
                validate_expr(expr, readable)
            except ExprError as e:
                errs.append(f"[{rid}] case#{i}.{label}: {e}")
    if rule.default is not None and rule.default != "keep" and isinstance(rule.default, str):
        try:
            validate_expr(rule.default, readable)
        except ExprError as e:
            errs.append(f"[{rid}] default: {e}")
    return errs
