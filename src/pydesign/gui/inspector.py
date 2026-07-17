"""Selection geometry and source-provenance inspector."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pydesign.source import Frame


class GeometryInspector(QWidget):
    apply_requested = Signal(object)
    reveal_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setAccessibleName("Selection inspector")
        self.object_id = QLabel("No selection")
        self.source = QLabel("—")
        self.source.setWordWrap(True)
        self.ownership = QLabel("—")
        self.fields = [self._field() for _ in range(4)]
        form = QFormLayout()
        form.addRow("Object", self.object_id)
        form.addRow("Source", self.source)
        form.addRow("Ownership", self.ownership)
        for label, field in zip(("X", "Y", "Width", "Height"), self.fields, strict=True):
            form.addRow(label, field)
        apply_button = QPushButton("Apply geometry")
        apply_button.clicked.connect(self._apply)
        reveal_button = QPushButton("Reveal in Python")
        reveal_button.clicked.connect(self.reveal_requested)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Inspector"))
        layout.addLayout(form)
        layout.addWidget(apply_button)
        layout.addWidget(reveal_button)
        layout.addStretch(1)
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
    ) -> None:
        self.object_id.setText(object_id or "No selection")
        self.source.setText(source)
        self.ownership.setText(ownership)
        self.set_enabled(bool(object_id and frame))
        if frame is not None:
            for field, value in zip(self.fields, frame, strict=True):
                field.setValue(value)

    def set_enabled(self, enabled: bool) -> None:
        for field in self.fields:
            field.setEnabled(enabled)

    def frame(self) -> Frame:
        return tuple(field.value() for field in self.fields)  # type: ignore[return-value]

    def _apply(self) -> None:
        self.apply_requested.emit(self.frame())
