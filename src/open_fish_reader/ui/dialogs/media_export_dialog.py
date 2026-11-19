from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...domain.media_export import MediaExportRequest
from ...domain.taxon import Taxon
from ...version import APP_NAME


class MediaExportDialog(QDialog):
    DESTINATION_KEY = "exports/destination_folder"
    GROUP_KEY = "exports/group_by_taxon"

    def __init__(
        self,
        taxa: list[Taxon],
        *,
        image_available: bool,
        video_available: bool,
        selected_taxon_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._taxa_by_id = {taxon.id: taxon for taxon in taxa}
        self._settings = QSettings(APP_NAME, APP_NAME)
        self.setWindowTitle("Exporter le média")
        self.resize(590, 300)

        self.taxon_combo = QComboBox()
        self.taxon_combo.addItem("Aucun taxon", None)
        for taxon in taxa:
            self.taxon_combo.addItem(f"{taxon.tax_code} — {taxon.common_name}", taxon.id)
        if selected_taxon_id is not None:
            index = self.taxon_combo.findData(selected_taxon_id)
            if index >= 0:
                self.taxon_combo.setCurrentIndex(index)

        self.image_checkbox = QCheckBox("Image affichée (PNG)")
        self.image_checkbox.setEnabled(image_available)
        self.image_checkbox.setChecked(image_available)
        self.video_checkbox = QCheckBox("Séquence vidéo complète")
        self.video_checkbox.setEnabled(video_available)

        self.destination_edit = QLineEdit(self._settings.value(self.DESTINATION_KEY, "", type=str))
        browse_button = QPushButton("Parcourir…")
        destination_layout = QHBoxLayout()
        destination_layout.addWidget(self.destination_edit, stretch=1)
        destination_layout.addWidget(browse_button)

        self.group_checkbox = QCheckBox("Ranger dans un sous-dossier par espèce")
        self.group_checkbox.setChecked(self._settings.value(self.GROUP_KEY, True, type=bool))

        form = QFormLayout()
        form.addRow("Taxon", self.taxon_combo)
        form.addRow("", self.image_checkbox)
        form.addRow("", self.video_checkbox)
        form.addRow("Dossier", destination_layout)
        form.addRow("", self.group_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Exporter")
        browse_button.clicked.connect(self._browse)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def request(self) -> MediaExportRequest:
        taxon_id = self.taxon_combo.currentData()
        taxon = self._taxa_by_id.get(taxon_id)
        return MediaExportRequest(
            destination_folder=Path(self.destination_edit.text().strip()),
            taxon_code=taxon.tax_code if taxon else None,
            taxon_common_name=taxon.common_name if taxon else None,
            export_image=self.image_checkbox.isChecked(),
            export_video=self.video_checkbox.isChecked(),
            group_by_taxon=self.group_checkbox.isChecked(),
        )

    def _browse(self) -> None:
        initial = self.destination_edit.text().strip()
        path = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier d'export",
            initial,
        )
        if path:
            self.destination_edit.setText(path)

    def _validate_and_accept(self) -> None:
        request = self.request()
        if not request.export_image and not request.export_video:
            QMessageBox.warning(self, "Export incomplet", "Cochez l'image, la vidéo ou les deux.")
            return
        if not str(request.destination_folder):
            QMessageBox.warning(self, "Dossier manquant", "Choisissez un dossier de destination.")
            return
        try:
            request.destination_folder.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            QMessageBox.critical(self, "Dossier inaccessible", str(error))
            return
        self._settings.setValue(self.DESTINATION_KEY, str(request.destination_folder))
        self._settings.setValue(self.GROUP_KEY, request.group_by_taxon)
        self.accept()
