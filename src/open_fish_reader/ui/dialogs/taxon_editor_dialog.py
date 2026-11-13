from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class TaxonEditorValue:
    tax_code: str
    common_name: str
    scientific_name: str
    sandre_code: str | None
    stage_code: int
    stage_label: str
    is_active: bool
    display_order: int
    keyboard_shortcut: str | None


class TaxonEditorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        initial: TaxonEditorValue | None = None,
        code_editable: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Ajouter un taxon/stade" if initial is None else "Modifier le taxon/stade"
        )
        self.resize(460, 420)

        self.code_edit = QLineEdit(initial.tax_code if initial else "")
        self.code_edit.setMaxLength(12)
        self.code_edit.setEnabled(code_editable)
        self.common_name_edit = QLineEdit(initial.common_name if initial else "")
        self.scientific_name_edit = QLineEdit(initial.scientific_name if initial else "")
        self.sandre_code_edit = QLineEdit(initial.sandre_code or "" if initial else "")
        self.stage_code_spin = QSpinBox()
        self.stage_code_spin.setRange(0, 99)
        self.stage_code_spin.setValue(initial.stage_code if initial else 5)
        self.stage_label_edit = QLineEdit(initial.stage_label if initial else "adulte")
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
        form.addRow("Code stade *", self.stage_code_spin)
        form.addRow("Libellé du stade *", self.stage_label_edit)
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
        shortcut = self.shortcut_edit.text().strip().upper() or None
        return TaxonEditorValue(
            tax_code=self.code_edit.text().strip().upper(),
            common_name=self.common_name_edit.text().strip(),
            scientific_name=self.scientific_name_edit.text().strip(),
            sandre_code=self.sandre_code_edit.text().strip() or None,
            stage_code=self.stage_code_spin.value(),
            stage_label=self.stage_label_edit.text().strip(),
            is_active=self.active_checkbox.isChecked(),
            display_order=self.order_spin.value(),
            keyboard_shortcut=shortcut,
        )

    def _validate_and_accept(self) -> None:
        value = self.value()
        missing = []
        if not value.tax_code:
            missing.append("code court")
        if not value.common_name:
            missing.append("nom commun")
        if not value.scientific_name:
            missing.append("nom scientifique")
        if not value.stage_label:
            missing.append("libellé du stade")
        if missing:
            QMessageBox.warning(
                self,
                "Informations manquantes",
                "Renseignez : " + ", ".join(missing) + ".",
            )
            return
        if not value.tax_code.replace("_", "").isalnum():
            QMessageBox.warning(
                self,
                "Code invalide",
                "Le code court ne peut contenir que des lettres, chiffres ou soulignés.",
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
