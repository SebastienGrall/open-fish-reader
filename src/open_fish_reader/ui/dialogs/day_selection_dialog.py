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
    day_selected = Signal(Path)

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
        for day_folder in sorted(day_folders, reverse=True):
            event_count, part_count = indexed_days.get(day_folder.name, (0, 0))
            if event_count or part_count:
                status = f"Indexée : {event_count} événements, {part_count} parties"
            else:
                status = "Non indexée"
            display_date = datetime.strptime(day_folder.name, "%Y-%m-%d").strftime("%d/%m/%Y")
            item = QListWidgetItem(f"{display_date}    {status}")
            item.setData(Qt.ItemDataRole.UserRole, str(day_folder))
            self.days_list.addItem(item)

        self.open_button = QPushButton("Ouvrir la journée")
        self.open_button.setDefault(True)
        self.open_button.setEnabled(self.days_list.currentItem() is not None)
        refresh_button = QPushButton("Réindexer")
        cancel_button = QPushButton("Fermer")

        self.days_list.currentItemChanged.connect(
            lambda current, _previous: self.open_button.setEnabled(current is not None)
        )
        self.days_list.itemDoubleClicked.connect(lambda _item: self._accept_selection())
        self.open_button.clicked.connect(self._accept_selection)
        refresh_button.clicked.connect(self._accept_selection)
        cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(refresh_button)
        buttons.addWidget(self.open_button)
        buttons.addWidget(cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self.days_list)
        layout.addLayout(buttons)

        if self.days_list.count():
            self.days_list.setCurrentRow(0)

    def _accept_selection(self) -> None:
        item = self.days_list.currentItem()
        if item is None:
            return
        self.day_selected.emit(Path(item.data(Qt.ItemDataRole.UserRole)))
        self.accept()
