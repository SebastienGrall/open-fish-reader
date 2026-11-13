from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class CompactVideoHeader(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.station_label = QLabel("Station : -")
        self.day_label = QLabel("Journée : -")
        self.file_label = QLabel("Fichier : -")
        self.event_label = QLabel("Événement : -")
        self.part_label = QLabel("Partie : -")
        self.frame_label = QLabel("Image : -")
        self.timestamp_label = QLabel("Heure : -")

        first_line = QHBoxLayout()
        first_line.setContentsMargins(0, 0, 0, 0)
        first_line.setSpacing(12)
        first_line.addWidget(self.station_label)
        first_line.addWidget(self.day_label)
        first_line.addWidget(self.file_label, stretch=1)
        first_line.addWidget(self.timestamp_label)

        second_line = QHBoxLayout()
        second_line.setContentsMargins(0, 0, 0, 0)
        second_line.setSpacing(12)
        second_line.addWidget(self.event_label, stretch=1)
        second_line.addWidget(self.part_label)
        second_line.addWidget(self.frame_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(2)
        layout.addLayout(first_line)
        layout.addLayout(second_line)

        for label in self.findChildren(QLabel):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.setStyleSheet(
            """
            CompactVideoHeader {
                background: palette(alternate-base);
            }

            CompactVideoHeader QLabel {
                padding: 1px 2px;
            }
            """
        )
