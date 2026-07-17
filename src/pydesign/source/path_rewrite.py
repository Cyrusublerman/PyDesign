"""Formatting-preserving source plans for editable cubic Bézier control points."""

from __future__ import annotations

import math
from pathlib import Path

import libcst as cst

from pydesign.source.analysis import build_source_index
from pydesign.source.cst_helpers import (
    adjust_scalar,
    call_id,
    ensure_pydesign_imports,
    is_direct_numeric,
    replace_scalar,
)
from pydesign.source.edits import (
    FrameStrategy,
    SourceEditPlan,
    SourceRewriteError,
)

type Point = tuple[float, float]
type BezierPoints = tuple[Point, Point, Point, Point]


def bezier_edit_options(project_root: str | Path, object_id: str) -> tuple[FrameStrategy, ...]:
    declaration = build_source_index(project_root).require(object_id)
    source = declaration.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    visitor = _BezierCoordinateVisitor(object_id)
    module.visit(visitor)
    if visitor.coordinates is None:
        return ("detach",)
    if all(is_direct_numeric(coordinate) for coordinate in visitor.coordinates):
        return ("safe", "adjust", "detach")
    return ("adjust", "detach")


def plan_bezier_update(
    project_root: str | Path,
    object_id: str,
    *,
    previous: BezierPoints,
    desired: BezierPoints,
    strategy: FrameStrategy = "safe",
) -> SourceEditPlan:
    if strategy == "edit_shared":
        raise SourceRewriteError("shared-name Bézier editing is not available yet")
    available = bezier_edit_options(project_root, object_id)
    if strategy not in available:
        raise SourceRewriteError(
            f"strategy {strategy!r} is not safe for {object_id!r}; "
            f"available: {', '.join(available)}"
        )
    declaration = build_source_index(project_root).require(object_id)
    if declaration.constructor != "BezierPath":
        raise SourceRewriteError(f"{object_id!r} does not identify a BezierPath")
    source = declaration.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    transformer = _BezierCoordinateTransformer(object_id, previous, desired, strategy)
    updated = module.visit(transformer)
    if not transformer.changed:
        raise SourceRewriteError(f"Bézier coordinates for {object_id!r} did not change")
    if transformer.requires_pt:
        updated = ensure_pydesign_imports(updated, {"pt"})
    return SourceEditPlan(
        path=declaration.path,
        before=source,
        after=updated.code,
        description=f"Update Bézier path {object_id}",
        object_id=object_id,
        property_name="commands",
        strategy=strategy,
    )


class _BezierCoordinateVisitor(cst.CSTVisitor):
    def __init__(self, object_id: str) -> None:
        self.object_id = object_id
        self.coordinates: tuple[cst.BaseExpression, ...] | None = None

    def visit_Call(self, node: cst.Call) -> None:
        if call_id(node) != self.object_id:
            return
        commands = _commands_argument(node)
        if commands is not None:
            self.coordinates = _coordinate_nodes(commands)


class _BezierCoordinateTransformer(cst.CSTTransformer):
    def __init__(
        self,
        object_id: str,
        previous: BezierPoints,
        desired: BezierPoints,
        strategy: FrameStrategy,
    ) -> None:
        self.object_id = object_id
        self.previous = _flatten(previous)
        self.desired = _flatten(desired)
        self.strategy = strategy
        self.changed = False
        self.requires_pt = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if call_id(original_node) != self.object_id:
            return updated_node
        arguments = list(updated_node.args)
        for index, argument in enumerate(arguments):
            if argument.keyword is None or argument.keyword.value != "commands":
                continue
            original_commands = original_node.args[index].value
            if not isinstance(original_commands, (cst.Tuple, cst.List)):
                raise SourceRewriteError("BezierPath commands must be a literal tuple/list")
            if not isinstance(argument.value, (cst.Tuple, cst.List)):
                raise SourceRewriteError("BezierPath commands must be a literal tuple/list")
            replacement = self._replace_commands(original_commands, argument.value)
            arguments[index] = argument.with_changes(value=replacement)
            return updated_node.with_changes(args=arguments)
        raise SourceRewriteError(f"BezierPath {self.object_id!r} has no commands property")

    def _replace_commands(
        self,
        original: cst.Tuple | cst.List,
        updated: cst.Tuple | cst.List,
    ) -> cst.Tuple | cst.List:
        original_calls = _command_calls(original)
        updated_calls = _command_calls(updated)
        if original_calls is None or updated_calls is None:
            if self.strategy != "detach":
                raise SourceRewriteError(
                    "GUI control editing requires MoveTo followed by one CurveTo"
                )
            self.changed = True
            self.requires_pt = True
            return _detached_commands(self.desired)
        move_original, curve_original = original_calls
        move_updated, curve_updated = updated_calls
        coordinates = [*move_original.args, *curve_original.args]
        updated_coordinates = [*move_updated.args, *curve_updated.args]
        for index, (original_arg, updated_arg) in enumerate(
            zip(coordinates, updated_coordinates, strict=True)
        ):
            if math.isclose(self.previous[index], self.desired[index], rel_tol=0.0, abs_tol=1e-9):
                continue
            if self.strategy == "safe":
                value = replace_scalar(original_arg.value, self.desired[index])
            elif self.strategy == "adjust":
                value = adjust_scalar(
                    original_arg.value, self.desired[index] - self.previous[index], detach=False
                )
                self.requires_pt = True
            else:
                value = adjust_scalar(original_arg.value, self.desired[index], detach=True)
                self.requires_pt = True
            updated_coordinates[index] = updated_arg.with_changes(value=value)
            self.changed = True
        move_count = len(move_updated.args)
        new_move = move_updated.with_changes(args=updated_coordinates[:move_count])
        new_curve = curve_updated.with_changes(args=updated_coordinates[move_count:])
        elements = list(updated.elements)
        elements[0] = elements[0].with_changes(value=new_move)
        elements[1] = elements[1].with_changes(value=new_curve)
        return updated.with_changes(elements=elements)


def _commands_argument(node: cst.Call) -> cst.Tuple | cst.List | None:
    for argument in node.args:
        if argument.keyword is not None and argument.keyword.value == "commands":
            return argument.value if isinstance(argument.value, (cst.Tuple, cst.List)) else None
    return None


def _coordinate_nodes(commands: cst.Tuple | cst.List) -> tuple[cst.BaseExpression, ...] | None:
    calls = _command_calls(commands)
    if calls is None:
        return None
    move, curve = calls
    return tuple(argument.value for argument in (*move.args, *curve.args))


def _command_calls(commands: cst.Tuple | cst.List) -> tuple[cst.Call, cst.Call] | None:
    if len(commands.elements) != 2 or any(element is None for element in commands.elements):
        return None
    first = commands.elements[0]
    second = commands.elements[1]
    if first is None or second is None:
        return None
    move = first.value
    curve = second.value
    if not isinstance(move, cst.Call) or not isinstance(curve, cst.Call):
        return None
    if not isinstance(move.func, cst.Name) or move.func.value != "MoveTo" or len(move.args) != 2:
        return None
    if (
        not isinstance(curve.func, cst.Name)
        or curve.func.value != "CurveTo"
        or len(curve.args) != 6
    ):
        return None
    return move, curve


def _flatten(points: BezierPoints) -> tuple[float, ...]:
    return tuple(coordinate for point in points for coordinate in point)


def _detached_commands(values: tuple[float, ...]) -> cst.Tuple:
    code = (
        f"(MoveTo({values[0]:.12g} * pt, {values[1]:.12g} * pt), "
        f"CurveTo({values[2]:.12g} * pt, {values[3]:.12g} * pt, "
        f"{values[4]:.12g} * pt, {values[5]:.12g} * pt, "
        f"{values[6]:.12g} * pt, {values[7]:.12g} * pt))"
    )
    expression = cst.parse_expression(code)
    if not isinstance(expression, cst.Tuple):
        raise AssertionError("detached Bézier commands must parse as a tuple")
    return expression
