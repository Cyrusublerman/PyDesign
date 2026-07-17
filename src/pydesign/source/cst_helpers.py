"""Shared formatting-preserving LibCST rewrite primitives."""

from __future__ import annotations

import math

import libcst as cst

from pydesign.source.analysis import quantity_parts
from pydesign.source.edits import Frame, SourceRewriteError

UNIT_POINTS = {
    "pt": 1.0,
    "inch": 72.0,
    "pc": 12.0,
    "mm": 72.0 / 25.4,
    "cm": 72.0 / 2.54,
    "px": 72.0 / 96.0,
}


def ensure_pydesign_imports(module: cst.Module, names: set[str]) -> cst.Module:
    transformer = _EnsureImportsTransformer(names)
    updated = module.visit(transformer)
    if not transformer.missing:
        return updated
    import_line = cst.SimpleStatementLine(
        [
            cst.ImportFrom(
                module=cst.Name("pydesign"),
                names=[cst.ImportAlias(cst.Name(name)) for name in sorted(transformer.missing)],
            )
        ]
    )
    body = list(updated.body)
    insertion = 0
    while insertion < len(body) and _is_header_line(body[insertion]):
        insertion += 1
    body.insert(insertion, import_line)
    return updated.with_changes(body=body)


def replace_scalar(node: cst.BaseExpression, desired_points: float) -> cst.BaseExpression:
    if isinstance(node, (cst.Integer, cst.Float)):
        return number_expression(desired_points)
    parts = quantity_parts(node)
    if parts is not None:
        _, unit = parts
        value = desired_points / UNIT_POINTS[unit]
        return cst.parse_expression(f"{number_code(value)} * {unit}")
    raise SourceRewriteError(
        f"safe replacement is unavailable for {cst.Module([]).code_for_node(node)!r}"
    )


def scalar_points(node: cst.BaseExpression) -> float | None:
    if isinstance(node, cst.Integer):
        return float(int(node.value, 0))
    if isinstance(node, cst.Float):
        return float(node.value)
    parts = quantity_parts(node)
    if parts is None:
        return None
    number, unit = parts
    if isinstance(number, cst.UnaryOperation) and isinstance(number.operator, cst.Minus):
        if isinstance(number.expression, cst.Integer):
            numeric = -float(int(number.expression.value, 0))
        elif isinstance(number.expression, cst.Float):
            numeric = -float(number.expression.value)
        else:
            return None
    elif isinstance(number, cst.Integer):
        numeric = float(int(number.value, 0))
    elif isinstance(number, cst.Float):
        numeric = float(number.value)
    else:
        return None
    return numeric * UNIT_POINTS[unit]


def adjust_scalar(node: cst.BaseExpression, value: float, *, detach: bool) -> cst.BaseExpression:
    if detach:
        return cst.parse_expression(point_code(value))
    if math.isclose(value, 0.0, abs_tol=1e-12):
        return node
    original = cst.Module([]).code_for_node(node)
    operator = "+" if value >= 0 else "-"
    return cst.parse_expression(f"({original}) {operator} {point_code(abs(value))}")


def frame_expression(frame: Frame) -> cst.BaseExpression:
    return cst.parse_expression(f"({', '.join(point_code(value) for value in frame)})")


def number_expression(value: float) -> cst.BaseExpression:
    return cst.parse_expression(number_code(value))


def number_code(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-9):
        return str(round(value))
    return format(value, ".8g")


def point_code(value: float) -> str:
    return f"{number_code(value)} * pt"


def is_direct_numeric(value: cst.BaseExpression) -> bool:
    return isinstance(value, (cst.Integer, cst.Float)) or quantity_parts(value) is not None


def call_id(node: cst.Call) -> str | None:
    for argument in node.args:
        if (
            argument.keyword is not None
            and argument.keyword.value == "id"
            and isinstance(argument.value, cst.SimpleString)
        ):
            value = argument.value.evaluated_value
            return value if isinstance(value, str) else None
    return None


class _EnsureImportsTransformer(cst.CSTTransformer):
    def __init__(self, names: set[str]) -> None:
        self.missing = set(names)

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        if (
            not isinstance(original_node.module, cst.Name)
            or original_node.module.value != "pydesign"
        ):
            return updated_node
        if isinstance(original_node.names, cst.ImportStar):
            self.missing.clear()
            return updated_node
        if isinstance(updated_node.names, cst.ImportStar):
            self.missing.clear()
            return updated_node
        aliases = list(updated_node.names)
        existing = {alias.evaluated_name for alias in original_node.names}
        additions = sorted(self.missing - existing)
        self.missing.difference_update(existing)
        if not additions:
            return updated_node
        aliases.extend(cst.ImportAlias(cst.Name(name)) for name in additions)
        self.missing.difference_update(additions)
        return updated_node.with_changes(names=aliases)


def _is_header_line(node: cst.CSTNode) -> bool:
    if not isinstance(node, cst.SimpleStatementLine) or not node.body:
        return False
    statement = node.body[0]
    if isinstance(statement, cst.Expr) and isinstance(statement.value, cst.SimpleString):
        return True
    return isinstance(statement, (cst.Import, cst.ImportFrom))
