"""Proofing workspace: PDF proof status and difference panes."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget


class ProofView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Proof view")
        self._status = QLabel("No proof run yet. Use Build → or `pydesign proof`.")
        self._status.setWordWrap(True)
        self._path = QLabel("—")
        self._path.setWordWrap(True)
        self._pdf_label = QLabel("PDF")
        self._diff_label = QLabel("Difference")
        self._pdf_image = QLabel("—")
        self._diff_image = QLabel("—")
        self._pdf_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._diff_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pdf_image.setMinimumHeight(160)
        self._diff_image.setMinimumHeight(160)
        panes = QHBoxLayout()
        pairs = (
            (self._pdf_label, self._pdf_image),
            (self._diff_label, self._diff_image),
        )
        for title, image in pairs:
            column = QVBoxLayout()
            column.addWidget(title)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(image)
            column.addWidget(scroll, 1)
            panes.addLayout(column, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Canvas / PDF Proof / Difference"))
        layout.addWidget(self._status)
        layout.addWidget(self._path)
        layout.addLayout(panes, 1)

    def set_proof_result(self, message: str, output_dir: Path | None = None) -> None:
        self._status.setText(message)
        self._path.setText(str(output_dir) if output_dir is not None else "—")
        if output_dir is None or not output_dir.is_dir():
            self._pdf_image.setText("—")
            self._diff_image.setText("—")
            return
        pages = sorted(output_dir.glob("page*.png"))
        diffs = sorted(output_dir.glob("diff-*.png"))
        smooth = Qt.TransformationMode.SmoothTransformation
        if pages:
            pixmap = QPixmap(str(pages[0]))
            self._pdf_image.setPixmap(pixmap.scaledToWidth(360, smooth))
        else:
            self._pdf_image.setText("No PDF raster")
        if diffs:
            pixmap = QPixmap(str(diffs[0]))
            self._diff_image.setPixmap(pixmap.scaledToWidth(360, smooth))
        else:
            self._diff_image.setText(
                "No difference image (add reference under .pydesign/proof/reference)"
            )
