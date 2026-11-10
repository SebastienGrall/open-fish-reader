from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class IndexingProgressDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Indexation de la journée")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.status_label = QLabel("Préparation de l'indexation...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.cancel_button = QPushButton("Annuler")

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.cancel_button)

    def update_progress(self, current: int, total: int, file_name: str) -> None:
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(current)
        self.status_label.setText(f"{current}/{total}    {file_name}")
