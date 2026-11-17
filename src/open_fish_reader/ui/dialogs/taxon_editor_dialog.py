from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...domain.development_stage import DevelopmentStage


@dataclass(frozen=True, slots=True)
class TaxonEditorValue:
    tax_code: str
    common_name: str
    scientific_name: str
    sandre_code: str | None
    stage_code: str | None
    is_active: bool
    display_order: int
    keyboard_shortcut: str | None


class TaxonEditorDialog(QDialog):
    def __init__(
        self,
        stages: list[DevelopmentStage],
        parent: QWidget | None = None,
        initial: TaxonEditorValue | None = None,
        code_editable: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajouter un taxon" if initial is None else "Modifier le taxon")
        self.resize(460, 390)

        self.code_edit = QLineEdit(initial.tax_code if initial else "")
        self.code_edit.setMaxLength(10)
        self.code_edit.setEnabled(code_editable)
        self.common_name_edit = QLineEdit(initial.common_name if initial else "")
        self.scientific_name_edit = QLineEdit(initial.scientific_name if initial else "")
        self.sandre_code_edit = QLineEdit(initial.sandre_code or "" if initial else "")

        self.stage_combo = QComboBox()
        self.stage_combo.addItem("Aucun stade", None)
        for stage in stages:
            self.stage_combo.addItem(f"{stage.label} [{stage.code}]", stage.code)
        if initial and initial.stage_code:
            index = self.stage_combo.findData(initial.stage_code)
            if index >= 0:
                self.stage_combo.setCurrentIndex(index)

        self.active_checkbox = QCheckBox("Afficher dans le panneau de saisie")
        self.active_checkbox.setChecked(initial.is_active if initial else True)
        self.order_spin = QSpinBox()
        self.order_spin.setRange(0, 9999)
        self.order_spin.setValue(initial.display_order if initial else 0)
        self.shortcut_edit = QLineEdit(initial.keyboard_shortcut or "" if initial else "")
        self.shortcut_edit.setMaxLength(1)
        self.shortcut_edit.setPlaceholderText("A-Z / 0-9")

        form = QFormLayout()
        form.addRow("Code court *", self.code_edit)
        form.addRow("Nom commun *", self.common_name_edit)
        form.addRow("Nom scientifique *", self.scientific_name_edit)
        form.addRow("Code SANDRE", self.sandre_code_edit)
        form.addRow("Stade", self.stage_combo)
        form.addRow("Ordre", self.order_spin)
        form.addRow("Raccourci", self.shortcut_edit)
        form.addRow("", self.active_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def value(self) -> TaxonEditorValue:
        return TaxonEditorValue(
            tax_code=self.code_edit.text().strip().upper(),
            common_name=self.common_name_edit.text().strip(),
            scientific_name=self.scientific_name_edit.text().strip(),
            sandre_code=self.sandre_code_edit.text().strip() or None,
            stage_code=self.stage_combo.currentData(),
            is_active=self.active_checkbox.isChecked(),
            display_order=self.order_spin.value(),
            keyboard_shortcut=self.shortcut_edit.text().strip().upper() or None,
        )

    def _validate_and_accept(self) -> None:
        value = self.value()
        if not value.tax_code or not value.common_name or not value.scientific_name:
            QMessageBox.warning(
                self,
                "Informations manquantes",
                "Le code, le nom commun et le nom scientifique sont obligatoires.",
            )
            return
        if not all(character.isalnum() or character in {"_", "-"} for character in value.tax_code):
            QMessageBox.warning(
                self,
                "Code invalide",
                "Le code accepte uniquement lettres, chiffres, '_' et '-'.",
            )
            return
        if value.keyboard_shortcut and not value.keyboard_shortcut.isalnum():
            QMessageBox.warning(
                self,
                "Raccourci invalide",
                "Le raccourci doit être une lettre ou un chiffre.",
            )
            return
        self.accept()
