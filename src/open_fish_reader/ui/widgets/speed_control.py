from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class SpeedControl(QWidget):
    decrease_requested = Signal()
    increase_requested = Signal()
    reset_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.decrease_button = QPushButton("-")
        self.value_button = QPushButton("x1")
        self.increase_button = QPushButton("+")

        self.decrease_button.setToolTip("Réduire la vitesse")
        self.value_button.setToolTip("Revenir à la vitesse x1")
        self.increase_button.setToolTip("Augmenter la vitesse")

        self.decrease_button.clicked.connect(self.decrease_requested)
        self.value_button.clicked.connect(self.reset_requested)
        self.increase_button.clicked.connect(self.increase_requested)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.decrease_button)
        layout.addWidget(self.value_button)
        layout.addWidget(self.increase_button)

    def set_speed(self, speed: float) -> None:
        text = f"x{speed:g}".replace(".", ",")
        self.value_button.setText(text)
