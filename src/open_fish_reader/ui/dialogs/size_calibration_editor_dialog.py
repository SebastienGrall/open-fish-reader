from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class SizeCalibrationValue:
    valid_from: datetime
    near_mm_per_pixel: float
    middle_mm_per_pixel: float
    far_mm_per_pixel: float
    comment: str | None


class SizeCalibrationEditorDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nouvelle relation taille / pixels")
        self.resize(440, 280)

        self.valid_from_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.valid_from_edit.setCalendarPopup(True)
        self.valid_from_edit.setDisplayFormat("dd/MM/yyyy HH:mm:ss")
        self.near_spin = self._ratio_spin()
        self.middle_spin = self._ratio_spin()
        self.far_spin = self._ratio_spin()
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("Ex. caméra repositionnée")

        form = QFormLayout()
        form.addRow("Valide à partir du *", self.valid_from_edit)
        form.addRow("Proche (mm/pixel) *", self.near_spin)
        form.addRow("Milieu (mm/pixel) *", self.middle_spin)
        form.addRow("Loin (mm/pixel) *", self.far_spin)
        form.addRow("Commentaire", self.comment_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @staticmethod
    def _ratio_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.000001, 9999.999999)
        spin.setDecimals(6)
        spin.setSingleStep(0.01)
        spin.setValue(1.0)
        spin.setSuffix(" mm/px")
        return spin

    def value(self) -> SizeCalibrationValue:
        return SizeCalibrationValue(
            valid_from=self.valid_from_edit.dateTime().toPython().astimezone(),
            near_mm_per_pixel=self.near_spin.value(),
            middle_mm_per_pixel=self.middle_spin.value(),
            far_mm_per_pixel=self.far_spin.value(),
            comment=self.comment_edit.text().strip() or None,
        )

    def _validate_and_accept(self) -> None:
        value = self.value()
        if (
            min(
                value.near_mm_per_pixel,
                value.middle_mm_per_pixel,
                value.far_mm_per_pixel,
            )
            <= 0
        ):
            QMessageBox.warning(
                self,
                "Calibration invalide",
                "Les trois ratios doivent être strictement positifs.",
            )
            return
        self.accept()
