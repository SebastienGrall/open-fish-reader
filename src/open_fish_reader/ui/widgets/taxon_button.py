from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QPushButton

from ...domain.taxon import Taxon


class TaxonButton(QPushButton):
    taxon_selected = Signal(object)

    def __init__(self, taxon: Taxon, parent=None) -> None:
        super().__init__(taxon.tax_code, parent)
        self.taxon = taxon
        self.setCheckable(True)
        self.setMinimumSize(54, 42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(
            f"{taxon.tax_code} — {taxon.common_name}\n"
            f"{taxon.scientific_name}\n"
            f"Stade {taxon.stage_code} : {taxon.stage_label}"
            + (f"\nRaccourci : {taxon.keyboard_shortcut}" if taxon.keyboard_shortcut else "")
        )
        self.clicked.connect(lambda: self.taxon_selected.emit(self.taxon))
