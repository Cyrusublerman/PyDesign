"""Selection geometry, appearance and sectioned inspector dock content."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pydesign.source import Frame

_STUB_SECTIONS = (
    ("Image", "Stage 6"),
    ("Flow", "Stage 5"),
    ("Accessibility", "Stage 5"),
    ("Constraints", "Stage 5"),
)


class GeometryInspector(QWidget):
    apply_requested = Signal(object)
    appearance_requested = Signal(object)
    reveal_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setAccessibleName("Selection inspector")
        self.object_id = QLabel("No selection")
        self.source = QLabel("—")
        self.source.setWordWrap(True)
        self.ownership = QLabel("—")
        self.style_provenance = QLabel("No style= reference")
        self.fields = [self._field() for _ in range(4)]
        geometry = QGroupBox("Geometry")
        form = QFormLayout(geometry)
        form.addRow("Object", self.object_id)
        for label, field in zip(("X", "Y", "Width", "Height"), self.fields, strict=True):
            form.addRow(label, field)
        apply_button = QPushButton("Apply geometry")
        apply_button.clicked.connect(self._apply)
        form.addRow(apply_button)
        source_box = QGroupBox("Source")
        source_form = QFormLayout(source_box)
        source_form.addRow("Path", self.source)
        source_form.addRow("Ownership", self.ownership)
        reveal_button = QPushButton("Reveal in Python")
        reveal_button.clicked.connect(self.reveal_requested)
        source_form.addRow(reveal_button)
        appearance = QGroupBox("Appearance")
        appearance_form = QFormLayout(appearance)
        self.fill = QLineEdit()
        self.stroke = QLineEdit()
        self.stroke_width = self._field()
        self.colour = QLineEdit()
        self.text = QLineEdit()
        appearance_form.addRow("Fill", self.fill)
        appearance_form.addRow("Stroke", self.stroke)
        appearance_form.addRow("Stroke width", self.stroke_width)
        appearance_form.addRow("Colour", self.colour)
        appearance_form.addRow("Text", self.text)
        apply_appearance = QPushButton("Apply appearance")
        apply_appearance.clicked.connect(self._apply_appearance)
        appearance_form.addRow(apply_appearance)
        styles = QGroupBox("Styles")
        styles_layout = QVBoxLayout(styles)
        styles_layout.addWidget(self.style_provenance)
        typography = QGroupBox("Typography")
        typography_layout = QVBoxLayout(typography)
        typography_layout.addWidget(
            QLabel("Shaped runs use TextFrame font=; Qt does not compose document text.")
        )
        body = QWidget()
        body_layout = QVBoxLayout(body)
        header = QLabel("Inspector")
        header.setObjectName("section-header")
        body_layout.addWidget(header)
        body_layout.addWidget(geometry)
        body_layout.addWidget(source_box)
        body_layout.addWidget(appearance)
        body_layout.addWidget(styles)
        body_layout.addWidget(typography)
        for title, stage in _STUB_SECTIONS:
            box = QGroupBox(title)
            box.setEnabled(False)
            box_layout = QVBoxLayout(box)
            box_layout.addWidget(QLabel(f"Not available yet ({stage})."))
            body_layout.addWidget(box)
        body_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        self.set_enabled(False)

    @staticmethod
    def _field() -> QDoubleSpinBox:
        field = QDoubleSpinBox()
        field.setRange(-1_000_000.0, 1_000_000.0)
        field.setDecimals(4)
        field.setSuffix(" pt")
        field.setKeyboardTracking(False)
        return field

    def set_selection(
        self,
        object_id: str,
        frame: Frame | None,
        *,
        source: str = "—",
        ownership: str = "—",
        style: str = "No style= reference",
        appearance: dict[str, object] | None = None,
    ) -> None:
        self.object_id.setText(object_id or "No selection")
        self.source.setText(source)
        self.ownership.setText(ownership)
        self.style_provenance.setText(style)
        self.set_enabled(bool(object_id and frame))
        if frame is not None:
            for field, value in zip(self.fields, frame, strict=True):
                field.setValue(value)
        values = appearance or {}
        self.fill.setText(str(values.get("fill", "") or ""))
        self.stroke.setText(str(values.get("stroke", "") or ""))
        raw_width = values.get("stroke_width", 1.0)
        try:
            self.stroke_width.setValue(float(raw_width))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            self.stroke_width.setValue(1.0)
        self.colour.setText(str(values.get("colour", "") or ""))
        self.text.setText(str(values.get("text", "") or ""))

    def set_enabled(self, enabled: bool) -> None:
        for field in self.fields:
            field.setEnabled(enabled)
        for widget in (self.fill, self.stroke, self.stroke_width, self.colour, self.text):
            widget.setEnabled(enabled)

    def frame(self) -> Frame:
        return tuple(field.value() for field in self.fields)  # type: ignore[return-value]

    def _apply(self) -> None:
        self.apply_requested.emit(self.frame())

    def _apply_appearance(self) -> None:
        self.appearance_requested.emit(
            {
                "fill": self.fill.text().strip() or None,
                "stroke": self.stroke.text().strip() or None,
                "stroke_width": self.stroke_width.value(),
                "colour": self.colour.text().strip() or None,
                "text": self.text.text(),
            }
        )
