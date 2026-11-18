from __future__ import annotations

import math
from itertools import pairwise

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class VideoWidget(QWidget):
    measurement_changed = Signal(object, float)
    measurement_finished = Signal(object, float)
    measurement_cancelled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: QImage | None = None
        self._measurement_active = False
        self._measurement_points: list[QPointF] = []
        self.setMinimumSize(640, 420)
        self.setStyleSheet("background-color: #111;")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def clear(self) -> None:
        self.cancel_measurement()
        self._image = None
        self.update()

    @property
    def measurement_active(self) -> bool:
        return self._measurement_active

    def start_measurement(self) -> bool:
        if self._image is None:
            return False
        self._measurement_active = True
        self._measurement_points.clear()
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocus()
        self.update()
        return True

    def cancel_measurement(self) -> None:
        had_measurement = self._measurement_active or bool(self._measurement_points)
        self._measurement_active = False
        self._measurement_points.clear()
        self.unsetCursor()
        self.update()
        if had_measurement:
            self.measurement_cancelled.emit()

    def undo_measurement_point(self) -> None:
        if self._measurement_active and self._measurement_points:
            self._measurement_points.pop()
            self._emit_changed()
            self.update()

    def finish_measurement(self) -> None:
        if not self._measurement_active or len(self._measurement_points) < 2:
            return

        points = self._serialized_points()
        length_pixels = self._length_pixels()

        self._measurement_active = False
        self._measurement_points.clear()
        self.unsetCursor()
        self.update()

        self.measurement_finished.emit(
            points,
            length_pixels,
        )

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self._image is None:
            painter.setPen(Qt.GlobalColor.lightGray)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aucune vidéo chargée")
            return
        target = self._image_target_rect()
        painter.drawPixmap(target.toRect(), QPixmap.fromImage(self._image))
        if self._measurement_points:
            self._paint_measurement(painter, target)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._measurement_active or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        point = self._widget_to_image(event.position())
        if point is None:
            return
        if len(self._measurement_points) >= 100:
            return
        self._measurement_points.append(point)
        self._emit_changed()
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._measurement_active and event.button() == Qt.MouseButton.LeftButton:
            # Le premier clic du double-clic a déjà ajouté le point final.
            self.finish_measurement()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._measurement_active:
            if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Z) and (
                event.key() == Qt.Key.Key_Backspace
                or event.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                self.undo_measurement_point()
                event.accept()
                return
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.finish_measurement()
                event.accept()
                return
            if event.key() == Qt.Key.Key_Escape:
                self.cancel_measurement()
                event.accept()
                return
        super().keyPressEvent(event)

    def _image_target_rect(self) -> QRectF:
        if self._image is None or self._image.isNull():
            return QRectF()
        scale = min(self.width() / self._image.width(), self.height() / self._image.height())
        width = self._image.width() * scale
        height = self._image.height() * scale
        return QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)

    def _widget_to_image(self, position: QPointF) -> QPointF | None:
        if self._image is None:
            return None
        target = self._image_target_rect()
        if not target.contains(position):
            return None
        x = (position.x() - target.left()) * self._image.width() / target.width()
        y = (position.y() - target.top()) * self._image.height() / target.height()
        return QPointF(x, y)

    def _image_to_widget(self, point: QPointF, target: QRectF) -> QPointF:
        assert self._image is not None
        return QPointF(
            target.left() + point.x() * target.width() / self._image.width(),
            target.top() + point.y() * target.height() / self._image.height(),
        )

    def _paint_measurement(self, painter: QPainter, target: QRectF) -> None:
        widget_points = [self._image_to_widget(point, target) for point in self._measurement_points]
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#00e5ff"), 3))
        for first, second in pairwise(widget_points):
            painter.drawLine(first, second)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(QColor("#ff3b30"))
        for point in widget_points:
            painter.drawEllipse(point, 5, 5)

    def _length_pixels(self) -> float:
        return sum(
            math.hypot(
                second.x() - first.x(),
                second.y() - first.y(),
            )
            for first, second in pairwise(self._measurement_points)
        )

    def _serialized_points(self) -> tuple[tuple[float, float], ...]:
        return tuple((point.x(), point.y()) for point in self._measurement_points)

    def _emit_changed(self) -> None:
        self.measurement_changed.emit(self._serialized_points(), self._length_pixels())
