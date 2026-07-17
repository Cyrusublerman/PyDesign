"""Static source ownership index keyed by stable document IDs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider


class OwnershipKind(StrEnum):
    LITERAL = "literal"
    QUANTITY = "quantity"
    TUPLE = "tuple"
    NAME = "name"
    EXPRESSION = "expression"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True)
class PropertyOwnership:
    name: str
    kind: OwnershipKind
    code: str
    span: SourceSpan
    components: tuple[OwnershipKind, ...] = ()


@dataclass(frozen=True, slots=True)
class Declaration:
    object_id: str
    constructor: str
    path: Path
    span: SourceSpan
    properties: tuple[PropertyOwnership, ...]

    def property(self, name: str) -> PropertyOwnership | None:
        return next((item for item in self.properties if item.name == name), None)


class DuplicateSourceIdError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourceIndex:
    root: Path
    declarations: tuple[Declaration, ...]

    def get(self, object_id: str) -> Declaration | None:
        return next((item for item in self.declarations if item.object_id == object_id), None)

    def require(self, object_id: str) -> Declaration:
        declaration = self.get(object_id)
        if declaration is None:
            raise KeyError(f"stable ID {object_id!r} was not found in project source")
        return declaration


def build_source_index(root: str | Path) -> SourceIndex:
    project_root = Path(root).expanduser().resolve()
    declarations: list[Declaration] = []
    seen: dict[str, Path] = {}
    ignored = {".git", ".pydesign", ".venv", "__pycache__", "exports"}
    for path in sorted(project_root.rglob("*.py")):
        if ignored.intersection(path.relative_to(project_root).parts):
            continue
        source = path.read_text(encoding="utf-8")
        module = cst.parse_module(source)
        visitor = _DeclarationVisitor(path)
        MetadataWrapper(module).visit(visitor)
        for declaration in visitor.declarations:
            previous = seen.get(declaration.object_id)
            if previous is not None:
                raise DuplicateSourceIdError(
                    f"stable ID {declaration.object_id!r} appears in both "
                    f"{previous.relative_to(project_root)} and {path.relative_to(project_root)}"
                )
            seen[declaration.object_id] = path
            declarations.append(declaration)
    return SourceIndex(project_root, tuple(declarations))


class _DeclarationVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, path: Path) -> None:
        self.path = path
        self.declarations: list[Declaration] = []

    def visit_Call(self, node: cst.Call) -> None:
        object_id = _call_id(node)
        if object_id is None:
            return
        position = self.get_metadata(PositionProvider, node)
        properties: list[PropertyOwnership] = []
        for argument in node.args:
            if argument.keyword is None:
                continue
            name = argument.keyword.value
            if name == "id":
                continue
            value_position = self.get_metadata(PositionProvider, argument.value)
            kind, components = classify_value(argument.value)
            properties.append(
                PropertyOwnership(
                    name=name,
                    kind=kind,
                    code=cst.Module([]).code_for_node(argument.value),
                    span=_span(value_position),
                    components=components,
                )
            )
        self.declarations.append(
            Declaration(
                object_id=object_id,
                constructor=_call_name(node.func),
                path=self.path,
                span=_span(position),
                properties=tuple(properties),
            )
        )


def classify_value(node: cst.BaseExpression) -> tuple[OwnershipKind, tuple[OwnershipKind, ...]]:
    if isinstance(node, (cst.Integer, cst.Float, cst.SimpleString)):
        return OwnershipKind.LITERAL, ()
    if _quantity_parts(node) is not None:
        return OwnershipKind.QUANTITY, ()
    if isinstance(node, (cst.Tuple, cst.List)):
        components = tuple(classify_value(element.value)[0] for element in node.elements if element)
        return OwnershipKind.TUPLE, components
    if isinstance(node, cst.Name):
        return OwnershipKind.NAME, ()
    return OwnershipKind.EXPRESSION, ()


def _quantity_parts(node: cst.BaseExpression) -> tuple[cst.BaseExpression, str] | None:
    sign = 1
    target = node
    if isinstance(target, cst.UnaryOperation) and isinstance(target.operator, cst.Minus):
        sign = -1
        target = target.expression
    if not isinstance(target, cst.BinaryOperation) or not isinstance(target.operator, cst.Multiply):
        return None
    number: cst.BaseExpression | None = None
    unit: cst.BaseExpression | None = None
    if isinstance(target.left, (cst.Integer, cst.Float)):
        number, unit = target.left, target.right
    elif isinstance(target.right, (cst.Integer, cst.Float)):
        number, unit = target.right, target.left
    if number is None or _unit_name(unit) is None:
        return None
    if sign == -1:
        number = cst.UnaryOperation(cst.Minus(), number)
    return number, _unit_name(unit) or ""


def quantity_parts(node: cst.BaseExpression) -> tuple[cst.BaseExpression, str] | None:
    return _quantity_parts(node)


def _unit_name(node: cst.BaseExpression | None) -> str | None:
    if isinstance(node, cst.Name):
        return node.value if node.value in {"pt", "mm", "cm", "inch", "pc", "px"} else None
    if isinstance(node, cst.Attribute):
        return (
            node.attr.value if node.attr.value in {"pt", "mm", "cm", "inch", "pc", "px"} else None
        )
    return None


def _call_id(node: cst.Call) -> str | None:
    for argument in node.args:
        if argument.keyword is None or argument.keyword.value != "id":
            continue
        if isinstance(argument.value, cst.SimpleString):
            value = argument.value.evaluated_value
            return value if isinstance(value, str) else None
    return None


def _call_name(node: cst.BaseExpression) -> str:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return node.attr.value
    return type(node).__name__


def _span(position: object) -> SourceSpan:
    # PositionProvider returns CodeRange; a helper keeps that dependency out of public dataclasses.
    start = position.start  # type: ignore[attr-defined]
    end = position.end  # type: ignore[attr-defined]
    return SourceSpan(start.line, start.column, end.line, end.column)
