"""Fit/Fill/Actual framing and touchpad pan/zoom for PageCanvas."""

from __future__ import annotations

from typing import Any, Literal

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QNativeGestureEvent, QWheelEvent
from PySide6.QtWidgets import QGraphicsView, QPinchGesture

from pydesign.gui.types import PageRegion

ViewMode = Literal["free", "fit", "fill", "actual", "fit_all"]
MIN_ZOOM = 0.05
MAX_ZOOM = 64.0
FIT_MARGIN = 0.07


class CanvasNavigationMixin:
    """View-mode and pointer-navigation behaviour mixed into PageCanvas."""

    canvas_scene: Any
    view_changed: Any
    page_changed: Any
    _page_regions: list[PageRegion]
    _view_mode: ViewMode
    _current_page: int
    _has_layout: bool
    _scroll_snap_armed: bool

    def zoom_factor(self) -> float:
        return float(self.transform().m11())  # type: ignore[attr-defined]

    def zoom_label(self) -> str:
        mode = self._view_mode.replace("_", " ").title()
        return f"Zoom: {self.zoom_factor() * 100:.0f}% · {mode}"

    def fit_page(self, index: int | None = None) -> None:
        if index is not None:
            self._current_page = index
        self._apply_view_mode("fit")

    def fill_width(self, index: int | None = None) -> None:
        if index is not None:
            self._current_page = index
        self._apply_view_mode("fill")

    def actual_size(self, index: int | None = None) -> None:
        if index is not None:
            self._current_page = index
        self._apply_view_mode("actual")

    def fit_all(self) -> None:
        self._apply_view_mode("fit_all")

    def zoom_by(self, factor: float, *, anchor: QPointF | None = None) -> None:
        self._view_mode = "free"
        current = self.zoom_factor()
        target = max(MIN_ZOOM, min(MAX_ZOOM, current * factor))
        scale = target / current if current else target
        if anchor is not None:
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)  # type: ignore[attr-defined]
        else:
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)  # type: ignore[attr-defined]
        self.scale(scale, scale)  # type: ignore[attr-defined]
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)  # type: ignore[attr-defined]
        self.view_changed.emit()

    def reset_zoom(self) -> None:
        self.actual_size()

    def go_to_page(self, index: int, *, prefer_fill: bool = False) -> None:
        if not self._page_regions:
            return
        self._current_page = max(0, min(index, len(self._page_regions) - 1))
        if prefer_fill or self._view_mode == "fill":
            self.fill_width(self._current_page)
        elif self._view_mode == "actual":
            self.actual_size(self._current_page)
        else:
            self.fit_page(self._current_page)
        self.page_changed.emit(self._current_page)

    def next_page(self) -> None:
        self.go_to_page(self._current_page + 1, prefer_fill=self._view_mode == "fill")

    def previous_page(self) -> None:
        self.go_to_page(self._current_page - 1, prefer_fill=self._view_mode == "fill")

    def _page_rect(self, index: int) -> QRectF | None:
        if not (0 <= index < len(self._page_regions)):
            return None
        page = self._page_regions[index]
        return QRectF(page.x, page.y, page.width, page.height)

    def _apply_view_mode(self, mode: ViewMode, *, announce: bool = True) -> None:
        if not self._page_regions:
            return
        self._view_mode = mode
        self._current_page = max(0, min(self._current_page, len(self._page_regions) - 1))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)  # type: ignore[attr-defined]
        if mode == "fit_all":
            bounds = self.canvas_scene.itemsBoundingRect().adjusted(-24, -24, 24, 24)
            self.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)  # type: ignore[attr-defined]
        elif mode == "actual":
            self.resetTransform()  # type: ignore[attr-defined]
            rect = self._page_rect(self._current_page)
            if rect is not None:
                self.centerOn(rect.center())  # type: ignore[attr-defined]
        else:
            rect = self._page_rect(self._current_page)
            if rect is None:
                return
            margin_x = rect.width() * FIT_MARGIN
            margin_y = rect.height() * FIT_MARGIN
            target = rect.adjusted(-margin_x, -margin_y, margin_x, margin_y)
            if mode == "fill":
                viewport = self.viewport().rect()  # type: ignore[attr-defined]
                if viewport.width() > 0 and rect.width() > 0:
                    scale = viewport.width() / rect.width()
                    scale = max(MIN_ZOOM, min(MAX_ZOOM, scale))
                    self.resetTransform()  # type: ignore[attr-defined]
                    self.scale(scale, scale)  # type: ignore[attr-defined]
                    self.centerOn(rect.center())  # type: ignore[attr-defined]
            else:
                self.fitInView(target, Qt.AspectRatioMode.KeepAspectRatio)  # type: ignore[attr-defined]
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)  # type: ignore[attr-defined]
        if announce:
            self.view_changed.emit()
            self.page_changed.emit(self._current_page)

    def _update_current_page_from_view(self) -> None:
        regions = getattr(self, "_page_regions", None)
        if not regions:
            return
        centre = self.mapToScene(self.viewport().rect().center())  # type: ignore[attr-defined]
        best = min(
            range(len(regions)),
            key=lambda index: abs((regions[index].y + regions[index].height / 2) - centre.y()),
        )
        if best != self._current_page:
            self._current_page = best
            self.page_changed.emit(self._current_page)

    def _snap_page_if_near(self) -> None:
        regions = getattr(self, "_page_regions", None)
        if not regions or getattr(self, "_view_mode", "fit") == "fit_all":
            return
        centre = self.mapToScene(self.viewport().rect().center())  # type: ignore[attr-defined]
        page = regions[self._current_page]
        page_centre_y = page.y + page.height / 2
        threshold = page.height * 0.2
        if abs(page_centre_y - centre.y()) <= threshold:
            self.centerOn(QPointF(page.x + page.width / 2, page_centre_y))  # type: ignore[attr-defined]
            self.view_changed.emit()

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)  # type: ignore[misc]
        if self._view_mode in {"fit", "fill", "actual", "fit_all"} and self._has_layout:
            self._apply_view_mode(self._view_mode, announce=True)

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)  # type: ignore[misc]
        if not hasattr(self, "_page_regions"):
            return
        self._update_current_page_from_view()
        self.view_changed.emit()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                delta = event.pixelDelta().y()
            if delta != 0:
                self.zoom_by(1.15 if delta > 0 else 1 / 1.15)
                event.accept()
                return
        pixel = event.pixelDelta()
        if not pixel.isNull():
            h = self.horizontalScrollBar()  # type: ignore[attr-defined]
            v = self.verticalScrollBar()  # type: ignore[attr-defined]
            h.setValue(h.value() - pixel.x())
            v.setValue(v.value() - pixel.y())
            self._scroll_snap_armed = True
            self._update_current_page_from_view()
            self.view_changed.emit()
            event.accept()
            return
        angle = event.angleDelta()
        if angle.y() != 0 or angle.x() != 0:
            h = self.horizontalScrollBar()  # type: ignore[attr-defined]
            v = self.verticalScrollBar()  # type: ignore[attr-defined]
            h.setValue(h.value() - angle.x())
            v.setValue(v.value() - angle.y())
            self._scroll_snap_armed = True
            self._update_current_page_from_view()
            self.view_changed.emit()
            event.accept()
            return
        super().wheelEvent(event)  # type: ignore[misc]

    def event(self, event: Any) -> bool:
        if (
            isinstance(event, QNativeGestureEvent)
            and event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture
        ):
            value = float(event.value())
            factor = 1.0 + value if abs(value) < 2 else value
            if factor > 0:
                self.zoom_by(factor)
            event.accept()
            return True
        if event.type() == QEvent.Type.Gesture:
            return self._gesture_event(event)
        if event.type() == QEvent.Type.Leave and self._scroll_snap_armed:
            self._scroll_snap_armed = False
            self._snap_page_if_near()
        return bool(super().event(event))  # type: ignore[misc]

    def _gesture_event(self, event: Any) -> bool:
        pinch = event.gesture(Qt.GestureType.PinchGesture)
        if pinch is not None and isinstance(pinch, QPinchGesture):
            if pinch.changeFlags() & QPinchGesture.ChangeFlag.ScaleFactorChanged:
                self.zoom_by(float(pinch.scaleFactor()))
            event.accept()
            return True
        return False
