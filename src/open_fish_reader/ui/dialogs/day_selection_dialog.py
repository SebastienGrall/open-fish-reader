from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DaySelectionDialog(QDialog):
    day_selected = Signal(Path, bool)

    def __init__(
        self,
        day_folders: list[Path],
        indexed_days: dict[str, tuple[int, int]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choisir une journée")
        self.resize(620, 480)
        title = QLabel("Sélectionnez la journée à dépouiller")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.days_list = QListWidget()
        for folder in sorted(day_folders, reverse=True):
            events, parts = indexed_days.get(folder.name, (0, 0))
            status = (
                f"Indexée : {events} événements, {parts} parties"
                if events or parts
                else "Non indexée"
            )
            date_text = datetime.strptime(folder.name, "%Y-%m-%d").strftime("%d/%m/%Y")
            item = QListWidgetItem(f"{date_text}    {status}")
            item.setData(Qt.ItemDataRole.UserRole, str(folder))
            self.days_list.addItem(item)
        open_button = QPushButton("Ouvrir la journée")
        refresh_button = QPushButton("Réindexer")
        close_button = QPushButton("Fermer")
        open_button.clicked.connect(lambda: self._select(False))
        refresh_button.clicked.connect(lambda: self._select(True))
        close_button.clicked.connect(self.reject)
        self.days_list.itemDoubleClicked.connect(lambda _item: self._select(False))
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(refresh_button)
        buttons.addWidget(open_button)
        buttons.addWidget(close_button)
        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self.days_list)
        layout.addLayout(buttons)
        if self.days_list.count():
            self.days_list.setCurrentRow(0)

    def _select(self, force: bool) -> None:
        item = self.days_list.currentItem()
        if item is None:
            return
        self.day_selected.emit(Path(item.data(Qt.ItemDataRole.UserRole)), force)
        self.accept()
