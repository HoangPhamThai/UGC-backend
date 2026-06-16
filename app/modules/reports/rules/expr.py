"""A tiny, safe expression language for rule conditions/formulas.
Parsed with ast.parse(mode="eval"); only whitelisted node types, the registry's
in-scope field names, and the functions round/min/max/abs are allowed. No
attribute access, no subscripting, no calls to anything else."""
import ast
import operator as _op
from typing import Any

_FUNCS = {"round": round, "min": min, "max": max, "abs": abs}

_BIN = {
    ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul,
    ast.Div: _op.truediv, ast.FloorDiv: _op.floordiv, ast.Mod: _op.mod,
}
_CMP = {
    ast.Lt: _op.lt, ast.LtE: _op.le, ast.Gt: _op.gt, ast.GtE: _op.ge,
    ast.Eq: _op.eq, ast.NotEq: _op.ne,
}
_ALLOWED_NODES = (
    ast.Expression, ast.Constant, ast.Name, ast.Load,
    ast.BinOp, ast.UnaryOp, ast.USub, ast.UAdd, ast.Not,
    ast.BoolOp, ast.And, ast.Or, ast.Compare, ast.IfExp, ast.Call,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
)


class ExprError(Exception):
    """Expression is syntactically invalid or uses a disallowed construct."""


def _parse(expr: str) -> ast.Expression:
    try:
        return ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ExprError(f"Cú pháp biểu thức không hợp lệ: {expr!r}") from e


def validate_expr(expr: str, allowed_names: set[str]) -> None:
    """Raise ExprError if `expr` uses any node, name, or call outside the whitelist."""
    tree = _parse(expr)
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ExprError(f"Cấu trúc không cho phép: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in _FUNCS):
                raise ExprError("Chỉ cho phép gọi round/min/max/abs")
        if isinstance(node, ast.Name) and node.id not in allowed_names and node.id not in _FUNCS:
            raise ExprError(f"Tên không hợp lệ: {node.id!r}")


def eval_expr(expr: str, namespace: dict[str, Any]) -> Any:
    """Evaluate `expr` against `namespace`. Call validate_expr first in the validator;
    at apply time bad input still raises ExprError rather than crashing the host."""
    tree = _parse(expr)
    return _eval(tree.body, namespace)


def _eval(node: ast.AST, ns: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in ns:
            raise ExprError(f"Thiếu giá trị cho {node.id!r}")
        return ns[node.id]
    if isinstance(node, ast.BinOp):
        return _BIN[type(node.op)](_eval(node.left, ns), _eval(node.right, ns))
    if isinstance(node, ast.UnaryOp):
        v = _eval(node.operand, ns)
        return -v if isinstance(node.op, ast.USub) else (not v if isinstance(node.op, ast.Not) else +v)
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, ns) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.Compare):
        left = _eval(node.left, ns)
        for op_node, comp in zip(node.ops, node.comparators):
            right = _eval(comp, ns)
            if not _CMP[type(op_node)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        return _eval(node.body, ns) if _eval(node.test, ns) else _eval(node.orelse, ns)
    if isinstance(node, ast.Call):
        fn = _FUNCS.get(getattr(node.func, "id", None))
        if fn is None:
            raise ExprError("Hàm không cho phép")
        return fn(*[_eval(a, ns) for a in node.args])
    raise ExprError(f"Không đánh giá được: {type(node).__name__}")
