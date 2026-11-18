from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...services.size_calibration_service import SizeCalibrationService
from ..models.size_calibration_table_model import SizeCalibrationTableModel
from .size_calibration_editor_dialog import SizeCalibrationEditorDialog


class SizeCalibrationDialog(QDialog):
    def __init__(
        self,
        database_path: Path,
        station_id: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.database_path = database_path
        self.station_id = station_id
        self.service = SizeCalibrationService()
        self.setWindowTitle("Relations taille / pixels")
        self.resize(980, 520)

        title = QLabel("Relations taille / pixels")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        description = QLabel(
            "Chaque calibration contient les ratios proche, milieu et loin. "
            "Une nouvelle calibration clôt automatiquement la précédente."
        )
        description.setWordWrap(True)
        add_button = QPushButton("Ajouter une calibration…")
        comment_button = QPushButton("Modifier le commentaire…")
        actions = QHBoxLayout()
        actions.addWidget(add_button)
        actions.addWidget(comment_button)
        actions.addStretch()

        self.model = SizeCalibrationTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(actions)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons)

        add_button.clicked.connect(self._add)
        comment_button.clicked.connect(self._edit_comment)
        self._reload()

    def _reload(self) -> None:
        self.model.set_items(self.service.list_for_station(self.database_path, self.station_id))
        self.table.resizeColumnsToContents()

    def _selected(self):
        index = self.table.currentIndex()
        return self.model.item_at(index.row()) if index.isValid() else None

    def _add(self) -> None:
        dialog = SizeCalibrationEditorDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.create(self.database_path, self.station_id, dialog.value())
        except ValueError as error:
            QMessageBox.warning(self, "Calibration invalide", str(error))
            return
        self._reload()

    def _edit_comment(self) -> None:
        item = self._selected()
        if item is None:
            QMessageBox.information(self, "Aucune calibration", "Sélectionnez une calibration.")
            return
        comment, accepted = QInputDialog.getText(
            self,
            "Modifier le commentaire",
            "Commentaire",
            text=item.comment or "",
        )
        if not accepted:
            return
        self.service.update_comment(self.database_path, item.id, comment.strip() or None)
        self._reload()
