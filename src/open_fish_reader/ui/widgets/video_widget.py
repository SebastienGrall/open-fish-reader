from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget


class VideoWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: QImage | None = None
        self.setMinimumSize(640, 420)
        self.setStyleSheet("background-color: #111;")

    def set_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def clear(self) -> None:
        self._image = None
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self._image is None:
            painter.setPen(Qt.GlobalColor.lightGray)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aucune vidéo chargée")
            return
        pixmap = QPixmap.fromImage(self._image)
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
