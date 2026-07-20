"""Simple vector tool icons painted into QIcons (no external assets)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _pixmap(size: int = 24) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


def _painter(pixmap: QPixmap) -> QPainter:
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    return painter


def _stroke(painter: QPainter, colour: str = "#1f2933", width: float = 1.6) -> None:
    pen = QPen(QColor(colour))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def icon_select() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    path = QPainterPath(QPointF(6, 4))
    path.lineTo(6, 20)
    path.lineTo(11, 15)
    path.lineTo(14, 21)
    path.lineTo(16.5, 20)
    path.lineTo(13.5, 14)
    path.lineTo(19, 14)
    path.closeSubpath()
    painter.setBrush(QColor("#e5e7eb"))
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def icon_direct_select() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    painter.drawLine(QPointF(5, 19), QPointF(12, 5))
    painter.drawLine(QPointF(12, 5), QPointF(19, 19))
    painter.setBrush(QColor("#ffffff"))
    for point in (QPointF(5, 19), QPointF(12, 5), QPointF(19, 19)):
        painter.drawRect(QRectF(point.x() - 2, point.y() - 2, 4, 4))
    painter.end()
    return QIcon(pixmap)


def icon_frame() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    painter.drawRect(QRectF(5, 6, 14, 12))
    painter.drawLine(QPointF(5, 10), QPointF(19, 10))
    painter.end()
    return QIcon(pixmap)


def icon_shape() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    painter.setBrush(QColor("#cbd5e1"))
    painter.drawRect(QRectF(5, 6, 14, 12))
    painter.end()
    return QIcon(pixmap)


def icon_rectangle() -> QIcon:
    return icon_shape()


def icon_ellipse() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    painter.setBrush(QColor("#cbd5e1"))
    painter.drawEllipse(QRectF(5, 6, 14, 12))
    painter.end()
    return QIcon(pixmap)


def icon_polygon() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    painter.setBrush(QColor("#cbd5e1"))
    path = QPainterPath(QPointF(12, 4))
    path.lineTo(20, 10)
    path.lineTo(17, 19)
    path.lineTo(7, 19)
    path.lineTo(4, 10)
    path.closeSubpath()
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def icon_pen() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    path = QPainterPath(QPointF(4, 18))
    path.cubicTo(QPointF(8, 8), QPointF(14, 8), QPointF(20, 6))
    painter.drawPath(path)
    painter.setBrush(QColor("#1f2933"))
    painter.drawEllipse(QRectF(18.5, 4.5, 3, 3))
    painter.end()
    return QIcon(pixmap)


def icon_line() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    painter.drawLine(QPointF(5, 18), QPointF(19, 6))
    painter.end()
    return QIcon(pixmap)


def icon_text() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter, width=1.8)
    painter.drawLine(QPointF(6, 6), QPointF(18, 6))
    painter.drawLine(QPointF(12, 6), QPointF(12, 19))
    painter.end()
    return QIcon(pixmap)


def icon_eyedropper() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    painter.drawLine(QPointF(7, 17), QPointF(16, 8))
    painter.drawRect(QRectF(15, 5, 4, 4))
    painter.end()
    return QIcon(pixmap)


def icon_hand() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    path = QPainterPath(QPointF(8, 14))
    path.lineTo(8, 9)
    path.cubicTo(QPointF(8, 7), QPointF(10, 7), QPointF(10, 9))
    path.lineTo(10, 12)
    path.lineTo(10, 7)
    path.cubicTo(QPointF(10, 5.5), QPointF(12, 5.5), QPointF(12, 7))
    path.lineTo(12, 12)
    path.lineTo(12, 8)
    path.cubicTo(QPointF(12, 6.5), QPointF(14, 6.5), QPointF(14, 8))
    path.lineTo(14, 13)
    path.lineTo(14, 10)
    path.cubicTo(QPointF(14, 8.5), QPointF(16, 8.5), QPointF(16, 10))
    path.lineTo(16, 15)
    path.cubicTo(QPointF(16, 18), QPointF(13, 20), QPointF(10, 20))
    path.cubicTo(QPointF(7, 20), QPointF(6, 17), QPointF(6, 15))
    path.closeSubpath()
    painter.setBrush(QColor("#e5e7eb"))
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def icon_zoom() -> QIcon:
    pixmap = _pixmap()
    painter = _painter(pixmap)
    _stroke(painter)
    painter.drawEllipse(QRectF(4, 4, 12, 12))
    painter.drawLine(QPointF(14, 14), QPointF(20, 20))
    painter.end()
    return QIcon(pixmap)


ICON_FOR_TOOL: dict[str, Callable[[], QIcon]] = {
    "select": icon_select,
    "direct_select": icon_direct_select,
    "frame": icon_frame,
    "shape": icon_shape,
    "rectangle": icon_rectangle,
    "ellipse": icon_ellipse,
    "polygon": icon_polygon,
    "pen": icon_pen,
    "bezier": icon_pen,
    "line": icon_line,
    "text": icon_text,
    "eyedropper": icon_eyedropper,
    "hand": icon_hand,
    "zoom": icon_zoom,
}


def icon_for(tool_id: str) -> QIcon:
    factory = ICON_FOR_TOOL.get(tool_id, icon_select)
    return factory()
