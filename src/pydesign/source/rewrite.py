"""LibCST-backed, formatting-preserving source edit planning."""

from __future__ import annotations

import base64
import math
import re
import secrets
from pathlib import Path

import libcst as cst

from pydesign.source.analysis import (
    Declaration,
    OwnershipKind,
    build_source_index,
)
from pydesign.source.cst_helpers import (
    adjust_scalar,
    call_id,
    ensure_pydesign_imports,
    frame_expression,
    is_direct_numeric,
    point_code,
    replace_scalar,
    scalar_points,
)
from pydesign.source.edits import (
    Frame,
    FrameStrategy,
    Point,
    SourceEditPlan,
    SourceRewriteError,
)


def frame_edit_options(declaration: Declaration) -> tuple[FrameStrategy, ...]:
    ownership = declaration.property("frame")
    if ownership is None:
        return ("detach",)
    if ownership.kind != OwnershipKind.TUPLE:
        return ("adjust", "detach")
    if all(
        item in {OwnershipKind.LITERAL, OwnershipKind.QUANTITY} for item in ownership.components
    ):
        return ("safe", "adjust", "detach")
    if all(
        item in {OwnershipKind.LITERAL, OwnershipKind.QUANTITY, OwnershipKind.NAME}
        for item in ownership.components
    ):
        return ("edit_shared", "adjust", "detach")
    return ("adjust", "detach")


def plan_frame_update(
    project_root: str | Path,
    object_id: str,
    *,
    previous: Frame,
    desired: Frame,
    strategy: FrameStrategy = "safe",
) -> SourceEditPlan:
    index = build_source_index(project_root)
    declaration = index.require(object_id)
    available = frame_edit_options(declaration)
    if strategy not in available:
        options = ", ".join(available)
        raise SourceRewriteError(
            f"strategy {strategy!r} is not safe for {object_id!r}; available: {options}"
        )
    source = declaration.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    shared_updates = (
        _collect_shared_updates(module, object_id, previous, desired)
        if strategy == "edit_shared"
        else {}
    )
    transformer = _FrameTransformer(object_id, previous, desired, strategy, module, shared_updates)
    updated = module.visit(transformer)
    if not transformer.changed:
        raise SourceRewriteError(
            f"frame property for {object_id!r} was not found or did not change"
        )
    if transformer.requires_pt:
        updated = ensure_pydesign_imports(updated, {"pt"})
    after = updated.code
    return SourceEditPlan(
        path=declaration.path,
        before=source,
        after=after,
        description=f"Update frame of {object_id}",
        object_id=object_id,
        property_name="frame",
        strategy=strategy,
    )


def plan_rectangle_insertion(
    project_root: str | Path,
    page_id: str,
    *,
    object_id: str,
    frame: Frame,
    fill: str = "#8d62d9",
) -> SourceEditPlan:
    index = build_source_index(project_root)
    if index.get(object_id) is not None:
        raise SourceRewriteError(f"stable ID {object_id!r} already exists")
    page = index.require(page_id)
    if page.constructor != "Page":
        raise SourceRewriteError(f"{page_id!r} does not identify a Page declaration")
    source = page.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    transformer = _RectangleInsertionTransformer(page_id, object_id, frame, fill)
    updated = module.visit(transformer)
    if not transformer.changed:
        raise SourceRewriteError(f"could not insert into Page {page_id!r}")
    updated = ensure_pydesign_imports(updated, {"Rectangle", "pt"})
    return SourceEditPlan(
        path=page.path,
        before=source,
        after=updated.code,
        description=f"Create rectangle {object_id}",
        object_id=object_id,
        property_name="elements",
        strategy="insert",
    )


def plan_bezier_insertion(
    project_root: str | Path,
    page_id: str,
    *,
    object_id: str,
    start: Point,
    control_1: Point,
    control_2: Point,
    end: Point,
    stroke: str = "#5b32a3",
) -> SourceEditPlan:
    index = build_source_index(project_root)
    if index.get(object_id) is not None:
        raise SourceRewriteError(f"stable ID {object_id!r} already exists")
    page = index.require(page_id)
    if page.constructor != "Page":
        raise SourceRewriteError(f"{page_id!r} does not identify a Page declaration")
    source = page.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    expression = cst.parse_expression(
        "BezierPath("
        f"id={object_id!r}, commands=("
        f"MoveTo({point_code(start[0])}, {point_code(start[1])}), "
        f"CurveTo({point_code(control_1[0])}, {point_code(control_1[1])}, "
        f"{point_code(control_2[0])}, {point_code(control_2[1])}, "
        f"{point_code(end[0])}, {point_code(end[1])})), "
        f"fill=None, stroke={stroke!r})"
    )
    transformer = _ElementInsertionTransformer(page_id, expression)
    updated = module.visit(transformer)
    if not transformer.changed:
        raise SourceRewriteError(f"could not insert into Page {page_id!r}")
    updated = ensure_pydesign_imports(updated, {"BezierPath", "CurveTo", "MoveTo", "pt"})
    return SourceEditPlan(
        path=page.path,
        before=source,
        after=updated.code,
        description=f"Create Bézier path {object_id}",
        object_id=object_id,
        property_name="elements",
        strategy="insert",
    )


class _FrameTransformer(cst.CSTTransformer):
    def __init__(
        self,
        object_id: str,
        previous: Frame,
        desired: Frame,
        strategy: FrameStrategy,
        module: cst.Module,
        shared_updates: dict[str, float],
    ) -> None:
        self.object_id = object_id
        self.previous = previous
        self.desired = desired
        self.strategy = strategy
        self.module = module
        self.changed = False
        self.requires_pt = False
        self._shared_updates = shared_updates

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if call_id(original_node) != self.object_id:
            return updated_node
        arguments = list(updated_node.args)
        for index, argument in enumerate(arguments):
            if argument.keyword is None or argument.keyword.value != "frame":
                continue
            original_argument = original_node.args[index]
            replacement = self._frame_value(original_argument.value)
            arguments[index] = argument.with_changes(value=replacement)
            self.changed = True
            return updated_node.with_changes(args=arguments)
        if self.strategy != "detach":
            raise SourceRewriteError(f"{self.object_id!r} has no explicit frame property")
        arguments.append(cst.Arg(keyword=cst.Name("frame"), value=frame_expression(self.desired)))
        self.requires_pt = True
        self.changed = True
        return updated_node.with_changes(args=arguments)

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        if self.strategy != "edit_shared" or len(original_node.targets) != 1:
            return updated_node
        target = original_node.targets[0].target
        if not isinstance(target, cst.Name) or target.value not in self._shared_updates:
            return updated_node
        delta = self._shared_updates[target.value]
        current = scalar_points(original_node.value)
        value = (
            replace_scalar(original_node.value, current + delta)
            if current is not None
            else adjust_scalar(original_node.value, delta, detach=False)
        )
        self.changed = True
        if not is_direct_numeric(value):
            self.requires_pt = True
        return updated_node.with_changes(value=value)

    def _frame_value(self, value: cst.BaseExpression) -> cst.BaseExpression:
        if not isinstance(value, (cst.Tuple, cst.List)) or len(value.elements) != 4:
            if self.strategy == "detach":
                self.requires_pt = True
                return frame_expression(self.desired)
            raise SourceRewriteError("frame must be a four-component tuple/list for this strategy")
        elements = list(value.elements)
        for index, element in enumerate(elements):
            if element is None or math.isclose(
                self.previous[index], self.desired[index], rel_tol=0.0, abs_tol=1e-9
            ):
                continue
            delta = self.desired[index] - self.previous[index]
            if self.strategy == "safe":
                replacement = replace_scalar(element.value, self.desired[index])
            elif self.strategy == "edit_shared":
                if isinstance(element.value, cst.Name):
                    continue
                replacement = replace_scalar(element.value, self.desired[index])
            elif self.strategy == "adjust":
                replacement = adjust_scalar(element.value, delta, detach=False)
                self.requires_pt = True
            else:
                replacement = adjust_scalar(element.value, self.desired[index], detach=True)
                self.requires_pt = True
            elements[index] = element.with_changes(value=replacement)
        return value.with_changes(elements=elements)


class _RectangleInsertionTransformer(cst.CSTTransformer):
    def __init__(self, page_id: str, object_id: str, frame: Frame, fill: str) -> None:
        self.page_id = page_id
        self.object_id = object_id
        self.frame = frame
        self.fill = fill
        self.changed = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if call_id(original_node) != self.page_id:
            return updated_node
        expression = cst.parse_expression(
            "Rectangle("
            f"id={self.object_id!r}, "
            f"frame=({point_code(self.frame[0])}, {point_code(self.frame[1])}, "
            f"{point_code(self.frame[2])}, {point_code(self.frame[3])}), "
            f"fill={self.fill!r})"
        )
        arguments = list(updated_node.args)
        for index, argument in enumerate(arguments):
            if argument.keyword is None or argument.keyword.value != "elements":
                continue
            if not isinstance(argument.value, (cst.List, cst.Tuple)):
                raise SourceRewriteError(
                    "Page elements must be a literal list/tuple for GUI insertion"
                )
            elements = list(argument.value.elements)
            elements.append(cst.Element(expression))
            arguments[index] = argument.with_changes(
                value=argument.value.with_changes(elements=elements)
            )
            self.changed = True
            return updated_node.with_changes(args=arguments)
        arguments.append(
            cst.Arg(keyword=cst.Name("elements"), value=cst.List([cst.Element(expression)]))
        )
        self.changed = True
        return updated_node.with_changes(args=arguments)


class _ElementInsertionTransformer(cst.CSTTransformer):
    def __init__(self, page_id: str, expression: cst.BaseExpression) -> None:
        self.page_id = page_id
        self.expression = expression
        self.changed = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if call_id(original_node) != self.page_id:
            return updated_node
        arguments = list(updated_node.args)
        for index, argument in enumerate(arguments):
            if argument.keyword is None or argument.keyword.value != "elements":
                continue
            if not isinstance(argument.value, (cst.List, cst.Tuple)):
                raise SourceRewriteError(
                    "Page elements must be a literal list/tuple for GUI insertion"
                )
            elements = [*argument.value.elements, cst.Element(self.expression)]
            arguments[index] = argument.with_changes(
                value=argument.value.with_changes(elements=elements)
            )
            self.changed = True
            return updated_node.with_changes(args=arguments)
        arguments.append(
            cst.Arg(keyword=cst.Name("elements"), value=cst.List([cst.Element(self.expression)]))
        )
        self.changed = True
        return updated_node.with_changes(args=arguments)


class _SharedUpdateVisitor(cst.CSTVisitor):
    def __init__(self, object_id: str, previous: Frame, desired: Frame) -> None:
        self.object_id = object_id
        self.previous = previous
        self.desired = desired
        self.updates: dict[str, float] = {}

    def visit_Call(self, node: cst.Call) -> None:
        if call_id(node) != self.object_id:
            return
        for argument in node.args:
            if argument.keyword is None or argument.keyword.value != "frame":
                continue
            if not isinstance(argument.value, (cst.Tuple, cst.List)):
                return
            for index, element in enumerate(argument.value.elements):
                if (
                    index >= 4
                    or element is None
                    or not isinstance(element.value, cst.Name)
                    or math.isclose(
                        self.previous[index], self.desired[index], rel_tol=0.0, abs_tol=1e-9
                    )
                ):
                    continue
                self.updates[element.value.value] = self.desired[index] - self.previous[index]


def _collect_shared_updates(
    module: cst.Module, object_id: str, previous: Frame, desired: Frame
) -> dict[str, float]:
    visitor = _SharedUpdateVisitor(object_id, previous, desired)
    module.visit(visitor)
    if not visitor.updates:
        raise SourceRewriteError("no changed frame component is controlled by a shared name")
    return visitor.updates


_ID_SANITIZE = re.compile(r"[^a-z0-9]+")


def suggested_id(prefix: str, existing: set[str]) -> str:
    base = _ID_SANITIZE.sub("-", prefix.lower()).strip("-") or "rectangle"
    candidate = base
    counter = 2
    while candidate in existing:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def new_gui_id(existing: set[str], *, random_bytes: bytes | None = None) -> str:
    """Return an opaque stable ID for an object created by direct manipulation."""

    while True:
        payload = random_bytes if random_bytes is not None else secrets.token_bytes(5)
        token = base64.b32encode(payload).decode("ascii").rstrip("=").lower()
        candidate = f"pd_{token}"
        if candidate not in existing:
            return candidate
        if random_bytes is not None:
            raise SourceRewriteError("the supplied deterministic GUI ID already exists")
