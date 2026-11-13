from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...domain.taxon import Taxon
from .taxon_button import TaxonButton


@dataclass(frozen=True, slots=True)
class ObservationDraft:
    taxon_id: int
    tax_code: str
    common_name: str
    stage_code: int
    stage_label: str
    individual_count: int
    direction: int
    confidence: str
    needs_review: bool
    length_mm: int | None
    glass_position: str
    comment: str


class QuickObservationPanel(QWidget):
    """Panneau de saisie rapide sans écriture SQLite dans cet incrément."""

    taxon_selected = Signal(object)
    draft_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(275)
        self.setMaximumWidth(390)
        self._selected_taxon: Taxon | None = None
        self._taxon_buttons: dict[int, TaxonButton] = {}

        title = QLabel("Observation rapide")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")

        self.selection_label = QLabel("Aucune espèce sélectionnée")
        self.selection_label.setWordWrap(True)
        self.selection_label.setStyleSheet(
            "font-weight: 600; padding: 7px; "
            "background: palette(alternate-base); border-radius: 4px;"
        )
        self.stage_label = QLabel("Stade : —")

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 99)
        self.count_spin.setValue(1)

        self.length_spin = QSpinBox()
        self.length_spin.setRange(0, 99_999)
        self.length_spin.setSpecialValueText("NA")
        self.length_spin.setSuffix(" mm")
        self.length_spin.setValue(0)

        self.glass_position_combo = QComboBox()
        self.glass_position_combo.addItem("Proche", "near")
        self.glass_position_combo.addItem("Milieu", "middle")
        self.glass_position_combo.addItem("Loin", "far")
        self.glass_position_combo.setCurrentIndex(1)

        self.confidence_combo = QComboBox()
        self.confidence_combo.addItem("Certain", "certain")
        self.confidence_combo.addItem("Probable", "probable")
        self.confidence_combo.addItem("Incertain", "uncertain")

        self.review_checkbox = QCheckBox("À revoir")
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("Commentaire facultatif")
        self.comment_edit.setClearButtonEnabled(True)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("Nombre", self.count_spin)
        form.addRow("Taille", self.length_spin)
        form.addRow("Position vitre", self.glass_position_combo)
        form.addRow("Confiance", self.confidence_combo)
        form.addRow("", self.review_checkbox)
        form.addRow("Commentaire", self.comment_edit)

        direction_group = QGroupBox("Sens et validation")
        direction_layout = QHBoxLayout(direction_group)
        self.downstream_button = self._direction_button("−1", "Dévalaison", -1)
        self.unknown_button = self._direction_button("0", "Indéterminé", 0)
        self.upstream_button = self._direction_button("+1", "Montaison", 1)
        direction_layout.addWidget(self.downstream_button)
        direction_layout.addWidget(self.unknown_button)
        direction_layout.addWidget(self.upstream_button)

        taxa_group = QGroupBox("Espèces actives")
        taxa_layout = QVBoxLayout(taxa_group)
        self.empty_taxa_label = QLabel(
            "Aucune espèce active. Utilisez Configuration pour en activer."
        )
        self.empty_taxa_label.setWordWrap(True)
        self.taxa_container = QWidget()
        self.taxa_grid = QGridLayout(self.taxa_container)
        self.taxa_grid.setContentsMargins(2, 2, 2, 2)
        self.taxa_grid.setSpacing(5)
        self.taxon_button_group = QButtonGroup(self)
        self.taxon_button_group.setExclusive(True)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(150)
        scroll.setWidget(self.taxa_container)
        taxa_layout.addWidget(self.empty_taxa_label)
        taxa_layout.addWidget(scroll, stretch=1)

        self.information_label = QLabel(
            "Cette étape valide l'ergonomie. Les boutons de sens ne sont pas encore enregistrés en base."
        )
        self.information_label.setWordWrap(True)
        self.information_label.setStyleSheet("color: palette(mid);")

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 7, 7, 7)
        layout.setSpacing(7)
        layout.addWidget(title)
        layout.addWidget(self.selection_label)
        layout.addWidget(self.stage_label)
        layout.addLayout(form)
        layout.addWidget(direction_group)
        layout.addWidget(separator)
        layout.addWidget(taxa_group, stretch=1)
        layout.addWidget(self.information_label)

        self._set_direction_enabled(False)

    @property
    def selected_taxon(self) -> Taxon | None:
        return self._selected_taxon

    def set_taxa(self, taxa: list[Taxon]) -> None:
        self._clear_taxon_buttons()
        self._selected_taxon = None
        self.selection_label.setText("Aucune espèce sélectionnée")
        self.stage_label.setText("Stade : —")
        self._set_direction_enabled(False)
        self.empty_taxa_label.setVisible(not taxa)

        columns = 4
        for position, taxon in enumerate(taxa):
            button = TaxonButton(taxon)
            button.taxon_selected.connect(self.select_taxon)
            self.taxon_button_group.addButton(button)
            self._taxon_buttons[taxon.id] = button
            self.taxa_grid.addWidget(
                button,
                position // columns,
                position % columns,
            )

    def select_taxon(self, taxon: Taxon) -> None:
        self._selected_taxon = taxon
        button = self._taxon_buttons.get(taxon.id)
        if button is not None:
            button.setChecked(True)
        self.selection_label.setText(f"{taxon.tax_code} — {taxon.common_name}")
        self.stage_label.setText(f"Stade {taxon.stage_code} : {taxon.stage_label}")
        self.count_spin.setValue(1)
        self._set_direction_enabled(True)
        self.taxon_selected.emit(taxon)

    def select_taxon_by_shortcut(self, key: str) -> bool:
        normalized = key.strip().upper()
        if not normalized:
            return False
        for button in self._taxon_buttons.values():
            if button.taxon.keyboard_shortcut == normalized:
                self.select_taxon(button.taxon)
                return True
        return False

    def reset_after_draft(self) -> None:
        # L'espèce reste sélectionnée pour accélérer les passages successifs.
        self.count_spin.setValue(1)
        self.length_spin.setValue(0)
        self.glass_position_combo.setCurrentIndex(1)
        self.confidence_combo.setCurrentIndex(0)
        self.review_checkbox.setChecked(False)
        self.comment_edit.clear()

    def _direction_button(self, text: str, tooltip: str, direction: int) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumHeight(42)
        button.setToolTip(tooltip)
        button.clicked.connect(lambda: self._request_draft(direction))
        return button

    def _request_draft(self, direction: int) -> None:
        taxon = self._selected_taxon
        if taxon is None:
            return
        length = self.length_spin.value() or None
        draft = ObservationDraft(
            taxon_id=taxon.id,
            tax_code=taxon.tax_code,
            common_name=taxon.common_name,
            stage_code=taxon.stage_code,
            stage_label=taxon.stage_label,
            individual_count=self.count_spin.value(),
            direction=direction,
            confidence=str(self.confidence_combo.currentData()),
            needs_review=self.review_checkbox.isChecked(),
            length_mm=length,
            glass_position=str(self.glass_position_combo.currentData()),
            comment=self.comment_edit.text().strip(),
        )
        self.draft_requested.emit(draft)

    def _set_direction_enabled(self, enabled: bool) -> None:
        self.downstream_button.setEnabled(enabled)
        self.unknown_button.setEnabled(enabled)
        self.upstream_button.setEnabled(enabled)

    def _clear_taxon_buttons(self) -> None:
        while self.taxa_grid.count():
            item = self.taxa_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self.taxon_button_group.removeButton(widget)
                widget.deleteLater()
        self._taxon_buttons.clear()
