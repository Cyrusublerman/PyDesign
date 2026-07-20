"""LibCST plans for scalar appearance and text properties."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import libcst as cst

from pydesign.source.analysis import OwnershipKind, build_source_index
from pydesign.source.cst_helpers import (
    call_id,
    ensure_pydesign_imports,
    replace_scalar,
    scalar_points,
)
from pydesign.source.edits import FrameStrategy, SourceEditPlan, SourceRewriteError

LiteralProperty = Literal["fill", "stroke", "colour", "text", "font"]
QuantityProperty = Literal["stroke_width", "font_size"]
STRING_PROPERTIES = frozenset({"fill", "stroke", "colour", "text", "font", "style"})
QUANTITY_PROPERTIES = frozenset({"stroke_width", "font_size"})


def literal_edit_options(declaration_kind: OwnershipKind | None) -> tuple[FrameStrategy, ...]:
    if declaration_kind is None:
        return ("detach",)
    if declaration_kind == OwnershipKind.LITERAL:
        return ("safe", "detach")
    if declaration_kind == OwnershipKind.NAME:
        return ("edit_shared", "detach")
    if declaration_kind == OwnershipKind.QUANTITY:
        return ("safe", "adjust", "detach")
    return ("adjust", "detach")


def plan_string_property_update(
    project_root: str | Path,
    object_id: str,
    property_name: str,
    *,
    desired: str | None,
    strategy: FrameStrategy = "safe",
) -> SourceEditPlan:
    if property_name not in STRING_PROPERTIES:
        raise SourceRewriteError(f"unsupported string property {property_name!r}")
    index = build_source_index(project_root)
    declaration = index.require(object_id)
    ownership = declaration.property(property_name)
    available = literal_edit_options(None if ownership is None else ownership.kind)
    if strategy not in available:
        raise SourceRewriteError(
            f"strategy {strategy!r} is not safe for {object_id}.{property_name}; "
            f"available: {', '.join(available)}"
        )
    source = declaration.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    transformer = _StringPropertyTransformer(object_id, property_name, desired, strategy)
    updated = module.visit(transformer)
    if not transformer.changed:
        raise SourceRewriteError(f"{property_name} for {object_id!r} did not change")
    return SourceEditPlan(
        path=declaration.path,
        before=source,
        after=updated.code,
        description=f"Update {property_name} of {object_id}",
        object_id=object_id,
        property_name=property_name,
        strategy=strategy,
    )


def plan_quantity_property_update(
    project_root: str | Path,
    object_id: str,
    property_name: str,
    *,
    desired_points: float,
    strategy: FrameStrategy = "safe",
) -> SourceEditPlan:
    if property_name not in QUANTITY_PROPERTIES:
        raise SourceRewriteError(f"unsupported quantity property {property_name!r}")
    index = build_source_index(project_root)
    declaration = index.require(object_id)
    ownership = declaration.property(property_name)
    available = literal_edit_options(None if ownership is None else ownership.kind)
    if strategy not in available:
        raise SourceRewriteError(
            f"strategy {strategy!r} is not safe for {object_id}.{property_name}; "
            f"available: {', '.join(available)}"
        )
    source = declaration.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    transformer = _QuantityPropertyTransformer(object_id, property_name, desired_points, strategy)
    updated = module.visit(transformer)
    if not transformer.changed:
        raise SourceRewriteError(f"{property_name} for {object_id!r} did not change")
    if transformer.requires_pt:
        updated = ensure_pydesign_imports(updated, {"pt"})
    return SourceEditPlan(
        path=declaration.path,
        before=source,
        after=updated.code,
        description=f"Update {property_name} of {object_id}",
        object_id=object_id,
        property_name=property_name,
        strategy=strategy,
    )


def style_edit_options(project_root: str | Path, object_id: str) -> tuple[FrameStrategy, ...]:
    declaration = build_source_index(project_root).require(object_id)
    ownership = declaration.property("style")
    return literal_edit_options(None if ownership is None else ownership.kind)


class _StringPropertyTransformer(cst.CSTTransformer):
    def __init__(
        self,
        object_id: str,
        property_name: str,
        desired: str | None,
        strategy: FrameStrategy,
    ) -> None:
        self.object_id = object_id
        self.property_name = property_name
        self.desired = desired
        self.strategy = strategy
        self.changed = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if call_id(original_node) != self.object_id:
            return updated_node
        value = _string_expression(self.desired)
        arguments = list(updated_node.args)
        for index, argument in enumerate(arguments):
            if argument.keyword is None or argument.keyword.value != self.property_name:
                continue
            if self.strategy == "safe":
                kind, _ = _classify(argument.value)
                if kind != OwnershipKind.LITERAL:
                    raise SourceRewriteError(
                        f"{self.object_id}.{self.property_name} is not a safe literal"
                    )
            arguments[index] = argument.with_changes(value=value)
            self.changed = True
            return updated_node.with_changes(args=arguments)
        if self.strategy != "detach":
            raise SourceRewriteError(
                f"{self.object_id!r} has no explicit {self.property_name} property"
            )
        arguments.append(cst.Arg(keyword=cst.Name(self.property_name), value=value))
        self.changed = True
        return updated_node.with_changes(args=arguments)


class _QuantityPropertyTransformer(cst.CSTTransformer):
    def __init__(
        self,
        object_id: str,
        property_name: str,
        desired_points: float,
        strategy: FrameStrategy,
    ) -> None:
        self.object_id = object_id
        self.property_name = property_name
        self.desired_points = desired_points
        self.strategy = strategy
        self.changed = False
        self.requires_pt = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if call_id(original_node) != self.object_id:
            return updated_node
        arguments = list(updated_node.args)
        for index, argument in enumerate(arguments):
            if argument.keyword is None or argument.keyword.value != self.property_name:
                continue
            current = scalar_points(argument.value)
            if self.strategy == "safe":
                if current is None:
                    raise SourceRewriteError(
                        f"{self.object_id}.{self.property_name} is not a safe quantity"
                    )
                replacement = replace_scalar(argument.value, self.desired_points)
            elif self.strategy == "adjust" and current is not None:
                from pydesign.source.cst_helpers import adjust_scalar

                replacement = adjust_scalar(
                    argument.value, self.desired_points - current, detach=False
                )
                self.requires_pt = True
            else:
                replacement = cst.parse_expression(f"{self.desired_points:g} * pt")
                self.requires_pt = True
            arguments[index] = argument.with_changes(value=replacement)
            self.changed = True
            return updated_node.with_changes(args=arguments)
        if self.strategy != "detach":
            raise SourceRewriteError(
                f"{self.object_id!r} has no explicit {self.property_name} property"
            )
        arguments.append(
            cst.Arg(
                keyword=cst.Name(self.property_name),
                value=cst.parse_expression(f"{self.desired_points:g} * pt"),
            )
        )
        self.requires_pt = True
        self.changed = True
        return updated_node.with_changes(args=arguments)


def _string_expression(value: str | None) -> cst.BaseExpression:
    if value is None:
        return cst.Name("None")
    return cst.SimpleString(repr(value))


def _classify(node: cst.BaseExpression) -> tuple[OwnershipKind, tuple[OwnershipKind, ...]]:
    from pydesign.source.analysis import classify_value

    return classify_value(node)
