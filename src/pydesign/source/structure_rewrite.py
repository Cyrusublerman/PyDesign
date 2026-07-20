"""Source plans for layer visibility and document page order."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from pydesign.source.analysis import build_source_index
from pydesign.source.cst_helpers import call_id
from pydesign.source.edits import SourceEditPlan, SourceRewriteError


def plan_layer_visibility_update(
    project_root: str | Path,
    layer_id: str,
    *,
    visible: bool,
) -> SourceEditPlan:
    index = build_source_index(project_root)
    declaration = index.require(layer_id)
    if declaration.constructor != "Layer":
        raise SourceRewriteError(f"{layer_id!r} is not a Layer declaration")
    source = declaration.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    transformer = _BooleanPropertyTransformer(layer_id, "visible", visible)
    updated = module.visit(transformer)
    if not transformer.changed:
        raise SourceRewriteError(f"visible property for {layer_id!r} did not change")
    state = "visible" if visible else "hidden"
    return SourceEditPlan(
        path=declaration.path,
        before=source,
        after=updated.code,
        description=f"Set layer {layer_id} {state}",
        object_id=layer_id,
        property_name="visible",
        strategy="safe",
    )


def plan_page_reorder(
    project_root: str | Path,
    document_id: str,
    *,
    current_page_ids: tuple[str, ...],
    desired_page_ids: tuple[str, ...],
) -> SourceEditPlan:
    if (
        len(current_page_ids) < 2
        or len(current_page_ids) != len(desired_page_ids)
        or set(current_page_ids) != set(desired_page_ids)
        or len(set(desired_page_ids)) != len(desired_page_ids)
    ):
        raise SourceRewriteError("page reorder requires a permutation of the current page ids")
    if current_page_ids == desired_page_ids:
        raise SourceRewriteError("page order is already current")
    index = build_source_index(project_root)
    declaration = index.require(document_id)
    if declaration.constructor != "Document":
        raise SourceRewriteError(f"{document_id!r} is not a Document declaration")
    source = declaration.path.read_text(encoding="utf-8")
    module = cst.parse_module(source)
    transformer = _PageOrderTransformer(document_id, current_page_ids, desired_page_ids)
    updated = module.visit(transformer)
    if not transformer.changed:
        raise SourceRewriteError(f"could not reorder pages on Document {document_id!r}")
    return SourceEditPlan(
        path=declaration.path,
        before=source,
        after=updated.code,
        description=f"Reorder pages on {document_id}",
        object_id=document_id,
        property_name="pages",
        strategy="safe",
    )


class _BooleanPropertyTransformer(cst.CSTTransformer):
    def __init__(self, object_id: str, property_name: str, value: bool) -> None:
        self.object_id = object_id
        self.property_name = property_name
        self.value = value
        self.changed = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if call_id(original_node) != self.object_id:
            return updated_node
        desired = cst.Name("True" if self.value else "False")
        arguments = list(updated_node.args)
        for index, argument in enumerate(arguments):
            if argument.keyword is None or argument.keyword.value != self.property_name:
                continue
            current = argument.value
            if isinstance(current, cst.Name) and current.value == desired.value:
                return updated_node
            arguments[index] = argument.with_changes(value=desired)
            self.changed = True
            return updated_node.with_changes(args=arguments)
        arguments.append(cst.Arg(keyword=cst.Name(self.property_name), value=desired))
        self.changed = True
        return updated_node.with_changes(args=arguments)


class _PageOrderTransformer(cst.CSTTransformer):
    def __init__(
        self,
        document_id: str,
        current_page_ids: tuple[str, ...],
        desired_page_ids: tuple[str, ...],
    ) -> None:
        self.document_id = document_id
        self.current_page_ids = current_page_ids
        self.desired_page_ids = desired_page_ids
        self.changed = False

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if call_id(original_node) != self.document_id:
            return updated_node
        arguments = list(updated_node.args)
        for index, argument in enumerate(arguments):
            if argument.keyword is None or argument.keyword.value != "pages":
                continue
            replacement = self._reorder_sequence(argument.value)
            if replacement is None:
                raise SourceRewriteError(
                    f"pages property for {self.document_id!r} is not a list/tuple "
                    "with one entry per page"
                )
            arguments[index] = argument.with_changes(value=replacement)
            self.changed = True
            return updated_node.with_changes(args=arguments)
        raise SourceRewriteError(f"{self.document_id!r} has no explicit pages property")

    def _reorder_sequence(self, node: cst.BaseExpression) -> cst.BaseExpression | None:
        if not isinstance(node, (cst.List, cst.Tuple)):
            return None
        elements = list(node.elements)
        if len(elements) != len(self.current_page_ids):
            return None
        by_id = {
            page_id: element
            for page_id, element in zip(self.current_page_ids, elements, strict=True)
        }
        ordered = [by_id[page_id] for page_id in self.desired_page_ids]
        return node.with_changes(elements=ordered)
