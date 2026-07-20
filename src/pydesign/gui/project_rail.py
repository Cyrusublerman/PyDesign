"""Project rail: Files, Pages and Layers tabs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ProjectRail(QWidget):
    file_activated = Signal(object)
    page_activated = Signal(int)
    layer_activated = Signal(str)
    layer_visibility_changed = Signal(str, bool)
    pages_reordered = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Project rail")
        self.file_list = QListWidget()
        self.file_list.setAccessibleName("Project Python files")
        self.file_list.currentItemChanged.connect(self._file_changed)
        self.page_list = QListWidget()
        self.page_list.setAccessibleName("Document pages")
        self.page_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.page_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.page_list.itemActivated.connect(self._page_activated)
        self.page_list.itemClicked.connect(self._page_activated)
        self.page_list.model().rowsMoved.connect(self._pages_moved)
        self.layer_tree = QTreeWidget()
        self.layer_tree.setHeaderHidden(True)
        self.layer_tree.setAccessibleName("Document layers")
        self.layer_tree.itemChanged.connect(self._layer_changed)
        self.layer_tree.itemClicked.connect(self._layer_clicked)
        self._layer_empty = QLabel("Layers appear after a successful Run.")
        self._layer_empty.setWordWrap(True)
        self._layer_suppress = False
        layers = QWidget()
        layers_layout = QVBoxLayout(layers)
        layers_layout.setContentsMargins(4, 4, 4, 4)
        layers_layout.addWidget(self.layer_tree, 1)
        layers_layout.addWidget(self._layer_empty)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.file_list, "Files")
        self.tabs.addTab(self.page_list, "Pages")
        self.tabs.addTab(layers, "Layers")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)

    def _file_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            return
        self.file_activated.emit(Path(str(current.data(Qt.ItemDataRole.UserRole))))

    def _page_activated(self, item: QListWidgetItem) -> None:
        self.page_activated.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _pages_moved(self, *_args: object) -> None:
        order = [
            str(self.page_list.item(row).data(Qt.ItemDataRole.UserRole + 1))
            for row in range(self.page_list.count())
        ]
        for row in range(self.page_list.count()):
            self.page_list.item(row).setData(Qt.ItemDataRole.UserRole, row)
        self.pages_reordered.emit(order)

    def _layer_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        self.layer_activated.emit(str(item.data(0, Qt.ItemDataRole.UserRole)))

    def _layer_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._layer_suppress or column != 0:
            return
        layer_id = str(item.data(0, Qt.ItemDataRole.UserRole))
        visible = item.checkState(0) == Qt.CheckState.Checked
        self.layer_visibility_changed.emit(layer_id, visible)

    def set_files(self, paths: list[tuple[str, Path]], selected: Path | None) -> None:
        self.file_list.blockSignals(True)
        self.file_list.clear()
        selected_item: QListWidgetItem | None = None
        for label, path in paths:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.file_list.addItem(item)
            if selected is not None and path == selected:
                selected_item = item
        self.file_list.blockSignals(False)
        if selected_item is not None:
            self.file_list.setCurrentItem(selected_item)

    def select_file(self, path: Path) -> None:
        for row in range(self.file_list.count()):
            item = self.file_list.item(row)
            if Path(str(item.data(Qt.ItemDataRole.UserRole))) == path:
                self.file_list.setCurrentItem(item)
                return

    def set_pages(self, pages: list[dict[str, Any]], current_index: int = 0) -> None:
        self.page_list.blockSignals(True)
        self.page_list.clear()
        for index, page in enumerate(pages):
            page_id = str(page.get("id", f"page-{index + 1}"))
            width = page.get("width", "?")
            height = page.get("height", "?")
            item = QListWidgetItem(f"{index + 1}. {page_id}  ({width}x{height})")
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setData(Qt.ItemDataRole.UserRole + 1, page_id)
            self.page_list.addItem(item)
        self.page_list.blockSignals(False)
        if pages:
            self.set_current_page(current_index)

    def set_current_page(self, index: int) -> None:
        if 0 <= index < self.page_list.count():
            self.page_list.setCurrentRow(index)

    def set_layers(self, layers: list[dict[str, Any]]) -> None:
        self._layer_suppress = True
        self.layer_tree.clear()
        if not layers:
            self._layer_empty.setText(
                "No layers in the current layout. Page-level elements appear without a layer row."
            )
            self._layer_suppress = False
            return
        self._layer_empty.setText("Toggle visibility to rewrite Layer(..., visible=…) in source.")
        for layer in layers:
            layer_id = str(layer.get("id", ""))
            label = str(layer.get("label") or layer_id)
            item = QTreeWidgetItem([label])
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setData(0, Qt.ItemDataRole.UserRole, layer_id)
            visible = bool(layer.get("visible", True))
            item.setCheckState(0, Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked)
            if not visible:
                item.setForeground(0, Qt.GlobalColor.gray)
            self.layer_tree.addTopLevelItem(item)
        self._layer_suppress = False
