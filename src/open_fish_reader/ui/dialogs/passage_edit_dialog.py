from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...domain.passage_edit import PassageEditValue
from ...domain.taxon import Taxon


class PassageEditDialog(QDialog):
    def __init__(
        self,
        passage: dict[str, object],
        taxa: list[Taxon],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._passage = passage
        self.setWindowTitle("Modifier le passage")
        self.resize(520, 470)

        self.taxon_combo = QComboBox()
        for taxon in taxa:
            stage = taxon.stage_label or "Aucun stade"
            self.taxon_combo.addItem(f"{taxon.tax_code} — {taxon.common_name} — {stage}", taxon.id)
        current_taxon = self.taxon_combo.findData(int(passage["taxon_id"]))
        if current_taxon >= 0:
            self.taxon_combo.setCurrentIndex(current_taxon)

        self.stage_label = QLabel()
        self.taxon_combo.currentIndexChanged.connect(self._update_stage)
        self._taxa_by_id = {taxon.id: taxon for taxon in taxa}
        self._update_stage()

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 99)
        self.count_spin.setValue(int(passage["individual_count"]))

        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Dévalaison (-1)", -1)
        self.direction_combo.addItem("Indéterminé (0)", 0)
        self.direction_combo.addItem("Montaison (+1)", 1)
        self.direction_combo.setCurrentIndex(
            self.direction_combo.findData(int(passage["direction"]))
        )

        self.confidence_combo = QComboBox()
        self.confidence_combo.addItem("Certain", "certain")
        self.confidence_combo.addItem("Probable", "probable")
        self.confidence_combo.addItem("Incertain", "uncertain")
        self.confidence_combo.setCurrentIndex(
            self.confidence_combo.findData(str(passage["confidence"]))
        )

        self.review_checkbox = QCheckBox("À revoir")
        self.review_checkbox.setChecked(bool(passage["needs_review"]))

        self.position_combo = QComboBox()
        self.position_combo.addItem("Proche", "near")
        self.position_combo.addItem("Milieu", "middle")
        self.position_combo.addItem("Loin", "far")
        self.position_combo.setCurrentIndex(
            self.position_combo.findData(str(passage["glass_position"]))
        )

        measured = str(passage["measurement_method"]) == "polyline_calibration"
        self.position_combo.setEnabled(not measured)
        self.comment_edit = QLineEdit(str(passage["comment"] or ""))

        info = QLabel(self._measurement_text(passage))
        info.setWordWrap(True)
        info.setStyleSheet("padding: 7px; background: palette(alternate-base);")

        form = QFormLayout()
        form.addRow("Horodatage", QLabel(str(passage["observed_at"])))
        form.addRow("Fichier", QLabel(str(passage["video_file_name"])))
        form.addRow("Image", QLabel(str(int(passage["frame_number"]) + 1)))
        form.addRow("Taxon", self.taxon_combo)
        form.addRow("Stade", self.stage_label)
        form.addRow("Nombre", self.count_spin)
        form.addRow("Sens", self.direction_combo)
        form.addRow("Confiance", self.confidence_combo)
        form.addRow("", self.review_checkbox)
        form.addRow("Position vitre", self.position_combo)
        form.addRow("Commentaire", self.comment_edit)
        form.addRow("Mesure", info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            "Enregistrer les modifications"
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def value(self) -> PassageEditValue:
        return PassageEditValue(
            taxon_id=int(self.taxon_combo.currentData()),
            individual_count=self.count_spin.value(),
            direction=int(self.direction_combo.currentData()),
            confidence=str(self.confidence_combo.currentData()),
            needs_review=self.review_checkbox.isChecked(),
            glass_position=str(self.position_combo.currentData()),
            comment=self.comment_edit.text().strip() or None,
        )

    def _update_stage(self) -> None:
        taxon_id = self.taxon_combo.currentData()
        taxon = self._taxa_by_id.get(taxon_id) if hasattr(self, "_taxa_by_id") else None
        if taxon is None:
            self.stage_label.setText("—")
        else:
            self.stage_label.setText(taxon.stage_label or "Aucun stade")

    def _accept_if_valid(self) -> None:
        if self.taxon_combo.currentData() is None:
            QMessageBox.warning(self, "Taxon manquant", "Sélectionnez un taxon.")
            return
        self.accept()

    @staticmethod
    def _measurement_text(passage: dict[str, object]) -> str:
        method = str(passage["measurement_method"])
        if method == "polyline_calibration":
            return (
                f"Mesure sur image : {float(passage['length_pixels']):.1f} px, "
                f"{int(passage['measurement_point_count'])} points, "
                f"{int(passage['length_mm'])} mm. "
                "Pour la refaire, supprimez puis recréez le passage."
            )
        if method == "manual":
            return f"Taille manuelle : {int(passage['length_mm'])} mm"
        return "Aucune mesure"
