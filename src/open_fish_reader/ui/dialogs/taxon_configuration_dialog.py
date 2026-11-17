from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...services.development_stage_service import (
    DevelopmentStageService,
)
from ...services.taxon_configuration_service import TaxonConfigurationService
from ...services.taxon_csv_service import (
    TaxonCsvService,
)
from ...services.taxon_management_service import TaxonManagementService
from ..delegates.taxon_shortcut_delegate import TaxonShortcutDelegate
from ..models.taxon_filter_proxy_model import TaxonFilterProxyModel
from ..models.taxon_table_model import TaxonColumns, TaxonTableModel
from .taxon_editor_dialog import TaxonEditorDialog, TaxonEditorValue


class TaxonConfigurationDialog(QDialog):
    def __init__(
        self,
        database_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.database_path = database_path

        self.service = TaxonConfigurationService()
        self.management_service = TaxonManagementService()
        self.csv_service = TaxonCsvService()
        self.development_stage_service = DevelopmentStageService()
        self.development_stages = []

        self.setWindowTitle("Espèces et raccourcis")
        self.resize(1120, 680)

        # Titre et description
        title = QLabel("Espèces et raccourcis")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        description = QLabel(
            "Activez les taxons à afficher dans "
            "le panneau de saisie, définissez leur "
            "ordre et attribuez au besoin une "
            "touche unique."
        )
        description.setWordWrap(True)

        # Recherche et filtre
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Rechercher par code, nom commun, nom scientifique, SANDRE ou stade…"
        )
        self.search_edit.setClearButtonEnabled(True)

        self.active_only_checkbox = QCheckBox("Actifs seulement")

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(
            self.search_edit,
            stretch=1,
        )
        filter_layout.addWidget(self.active_only_checkbox)

        # Actions sur les taxons
        add_button = QPushButton("Ajouter…")
        edit_button = QPushButton("Modifier…")
        archive_button = QPushButton("Archiver")

        select_visible_button = QPushButton("Activer les lignes visibles")
        clear_visible_button = QPushButton("Désactiver les lignes visibles")

        import_button = QPushButton("Importer CSV…")
        export_button = QPushButton("Exporter CSV…")

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(add_button)
        actions_layout.addWidget(edit_button)
        actions_layout.addWidget(archive_button)

        actions_layout.addSpacing(12)

        actions_layout.addWidget(select_visible_button)
        actions_layout.addWidget(clear_visible_button)

        actions_layout.addStretch()

        actions_layout.addWidget(import_button)
        actions_layout.addWidget(export_button)

        # Modèle et filtrage
        self.model = TaxonTableModel(self)

        self.proxy = TaxonFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)

        # Tableau
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(
            TaxonColumns.ORDER,
            Qt.SortOrder.AscendingOrder,
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )

        self.table.setItemDelegateForColumn(
            TaxonColumns.SHORTCUT,
            TaxonShortcutDelegate(self.table),
        )

        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setColumnWidth(
            TaxonColumns.ACTIVE,
            58,
        )
        self.table.setColumnWidth(
            TaxonColumns.ORDER,
            65,
        )
        self.table.setColumnWidth(
            TaxonColumns.CODE,
            60,
        )
        self.table.setColumnWidth(
            TaxonColumns.COMMON_NAME,
            175,
        )
        self.table.setColumnWidth(
            TaxonColumns.STAGE,
            90,
        )
        self.table.setColumnWidth(
            TaxonColumns.STAGE_CODE,
            85,
        )
        self.table.setColumnWidth(
            TaxonColumns.SANDRE,
            80,
        )
        self.table.setColumnWidth(
            TaxonColumns.SCIENTIFIC_NAME,
            210,
        )
        self.table.setColumnWidth(
            TaxonColumns.SHORTCUT,
            90,
        )

        # État et compteur
        self.status_label = QLabel()
        self.count_label = QLabel()

        status_layout = QHBoxLayout()
        status_layout.addWidget(
            self.status_label,
            stretch=1,
        )
        status_layout.addWidget(self.count_label)

        # Enregistrer / Annuler
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )

        self.save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("Enregistrer")

        # Mise en page générale
        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(filter_layout)
        layout.addLayout(actions_layout)
        layout.addWidget(
            self.table,
            stretch=1,
        )
        layout.addLayout(status_layout)
        layout.addWidget(self.buttons)

        # Recherche et filtrage
        self.search_edit.textChanged.connect(self.proxy.set_query)
        self.active_only_checkbox.toggled.connect(self.proxy.set_active_only)

        # Actions collectives
        select_visible_button.clicked.connect(lambda: self._set_visible_active(True))
        clear_visible_button.clicked.connect(lambda: self._set_visible_active(False))

        # CRUD
        add_button.clicked.connect(self._add_taxon)
        edit_button.clicked.connect(self._edit_selected_taxon)
        archive_button.clicked.connect(self._archive_selected_taxon)

        # Import et export CSV
        import_button.clicked.connect(self._import_csv)
        export_button.clicked.connect(self._export_csv)

        # Validation du modèle
        self.model.validation_changed.connect(self._validation_changed)
        self.model.dataChanged.connect(lambda *_args: self._refresh_count())

        # Validation ou annulation du dialogue
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)

        self._load()

    def _load(self) -> None:
        try:
            self.development_stages = self.development_stage_service.list_active(self.database_path)

            self.model.set_taxa(self.service.list_all(self.database_path))

            self._refresh_count()

        except (
            OSError,
            RuntimeError,
        ) as error:
            QMessageBox.critical(
                self,
                "Catalogue indisponible",
                str(error),
            )
            self.reject()

    def _set_visible_active(self, active: bool) -> None:
        state = Qt.CheckState.Checked if active else Qt.CheckState.Unchecked
        for proxy_row in range(self.proxy.rowCount()):
            proxy_index = self.proxy.index(proxy_row, TaxonColumns.ACTIVE)
            source_index = self.proxy.mapToSource(proxy_index)
            self.model.setData(source_index, state.value, Qt.ItemDataRole.CheckStateRole)
        self._refresh_count()

    def _validation_changed(self, valid: bool, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            "color: #238636;" if valid else "color: #cf222e; font-weight: 600;"
        )
        self.save_button.setEnabled(valid)

    def _refresh_count(self) -> None:
        self.count_label.setText(
            f"{self.model.active_count()} actif(s) / {self.model.rowCount()} taxons"
        )

    def _save(self) -> None:
        try:
            self.service.save_configuration(
                self.database_path,
                self.model.editable_taxa(),
            )
        except (ValueError, OSError, RuntimeError) as error:
            QMessageBox.warning(self, "Configuration invalide", str(error))
            return
        self.accept()

    def _selected_taxon(self):
        proxy_index = self.table.currentIndex()
        if not proxy_index.isValid():
            return None
        source_index = self.proxy.mapToSource(proxy_index)
        items = self.model.editable_taxa()
        return items[source_index.row()] if 0 <= source_index.row() < len(items) else None

    def _reload(self) -> None:
        self.model.set_taxa(self.service.list_all(self.database_path))
        self._refresh_count()

    def _add_taxon(self) -> None:
        dialog = TaxonEditorDialog(
            stages=self.development_stages,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.management_service.create(self.database_path, dialog.value())
        except ValueError as error:
            QMessageBox.warning(self, "Taxon invalide", str(error))
            return
        self._reload()

    def _edit_selected_taxon(self) -> None:
        item = self._selected_taxon()
        if item is None:
            return
        initial = TaxonEditorValue(
            tax_code=item.tax_code,
            common_name=item.common_name,
            scientific_name=item.scientific_name,
            sandre_code=item.sandre_code,
            stage_code=item.stage_code,
            is_active=item.is_active,
            display_order=item.display_order,
            keyboard_shortcut=item.keyboard_shortcut,
        )
        dialog = TaxonEditorDialog(
            stages=self.development_stages,
            parent=self,
            initial=initial,
            code_editable=False,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.management_service.update(self.database_path, item.id, dialog.value())
        except ValueError as error:
            QMessageBox.warning(self, "Taxon invalide", str(error))
            return
        self._reload()

    def _archive_selected_taxon(self) -> None:
        item = self._selected_taxon()
        if item is None:
            return
        answer = QMessageBox.question(
            self,
            "Archiver le taxon",
            f"Archiver {item.tax_code} — {item.common_name} ?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.management_service.archive(self.database_path, item.id)
        self._reload()

    def _import_csv(self) -> None:
        selected_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Importer un catalogue taxonomique",
            "",
            ("Fichiers CSV (*.csv);;Tous les fichiers (*)"),
        )

        if not selected_path:
            return

        answer = QMessageBox.question(
            self,
            "Importer le catalogue",
            (
                "Les lignes du fichier CSV seront "
                "ajoutées ou mettront à jour les taxons "
                "du catalogue de cette station.\n\n"
                "Le référentiel taxonomique protégé "
                "ne sera pas modifié.\n\n"
                "Continuer ?"
            ),
            (QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            imported_count = self.csv_service.import_station_catalog(
                self.database_path,
                Path(selected_path),
            )
        except (
            OSError,
            ValueError,
            RuntimeError,
        ) as error:
            QMessageBox.critical(
                self,
                "Import impossible",
                str(error),
            )
            return

        self._reload()

        QMessageBox.information(
            self,
            "Import terminé",
            (
                f"{imported_count} ligne(s) "
                "ont été importées ou mises à jour.\n\n"
                "Le référentiel protégé n'a pas "
                "été modifié."
            ),
        )

    def _export_csv(self) -> None:
        default_name = "catalogue_taxons_station.csv"

        selected_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exporter le catalogue taxonomique",
            default_name,
            ("Fichiers CSV (*.csv);;Tous les fichiers (*)"),
        )

        if not selected_path:
            return

        output_path = Path(selected_path)

        if output_path.suffix.lower() != ".csv":
            output_path = output_path.with_suffix(".csv")

        try:
            self.csv_service.export_station_catalog(
                self.database_path,
                output_path,
            )
        except (
            OSError,
            ValueError,
            RuntimeError,
        ) as error:
            QMessageBox.critical(
                self,
                "Export impossible",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "Export terminé",
            (f"Le catalogue de la station a été exporté dans :\n\n{output_path}"),
        )
