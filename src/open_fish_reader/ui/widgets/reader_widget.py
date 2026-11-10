from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .speed_control import SpeedControl
from .video_widget import VideoWidget


class ReaderWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.station_label = QLabel("Station : -")
        self.day_label = QLabel("Journée : -")
        self.file_label = QLabel("Fichier : -")
        self.event_label = QLabel("Événement : -")
        self.part_label = QLabel("Partie : -")
        self.frame_label = QLabel("Image : -")
        self.timestamp_label = QLabel("Horodatage : -")

        for label in (
            self.station_label,
            self.day_label,
            self.file_label,
            self.event_label,
            self.part_label,
            self.frame_label,
            self.timestamp_label,
        ):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        information_layout = QVBoxLayout()
        information_layout.setContentsMargins(0, 0, 0, 0)
        information_layout.addWidget(self.station_label)
        information_layout.addWidget(self.day_label)
        information_layout.addWidget(self.file_label)
        information_layout.addWidget(self.event_label)
        information_layout.addWidget(self.part_label)
        information_layout.addWidget(self.frame_label)
        information_layout.addWidget(self.timestamp_label)

        self.video_widget = VideoWidget()

        self.previous_file_button = QPushButton("Fichier précédent")
        self.play_pause_button = QPushButton("Lecture")
        self.speed_control = SpeedControl()
        self.next_file_button = QPushButton("Fichier suivant")
        self.previous_frame_button = QPushButton("Image précédente")
        self.next_frame_button = QPushButton("Image suivante")

        self.play_pause_button.setEnabled(False)
        self.previous_frame_button.setEnabled(False)
        self.next_frame_button.setEnabled(False)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.previous_file_button)
        controls_layout.addWidget(self.previous_frame_button)
        controls_layout.addStretch()
        controls_layout.addWidget(self.play_pause_button)
        controls_layout.addWidget(self.speed_control)
        controls_layout.addStretch()
        controls_layout.addWidget(self.next_frame_button)
        controls_layout.addWidget(self.next_file_button)

        layout = QVBoxLayout(self)
        layout.addLayout(information_layout)
        layout.addWidget(self.video_widget, stretch=1)
        layout.addLayout(controls_layout)

        self.set_file_navigation_enabled(False, False)

    def set_file_navigation_enabled(
        self,
        has_previous_file: bool,
        has_next_file: bool,
    ) -> None:
        self.previous_file_button.setEnabled(has_previous_file)
        self.next_file_button.setEnabled(has_next_file)

    def set_frame_navigation_enabled(
        self,
        has_previous_frame: bool,
        has_next_frame: bool,
    ) -> None:
        self.previous_frame_button.setEnabled(has_previous_frame)
        self.next_frame_button.setEnabled(has_next_frame)

    def set_navigation_enabled(
        self,
        has_previous_file: bool,
        has_next_file: bool,
    ) -> None:
        self.set_file_navigation_enabled(
            has_previous_file,
            has_next_file,
        )

    def clear_video_information(self) -> None:
        self.file_label.setText("Fichier : -")
        self.event_label.setText("Événement : -")
        self.part_label.setText("Partie : -")
        self.frame_label.setText("Image : -")
        self.timestamp_label.setText("Horodatage : -")
        self.video_widget.clear()
        self.set_frame_navigation_enabled(False, False)
