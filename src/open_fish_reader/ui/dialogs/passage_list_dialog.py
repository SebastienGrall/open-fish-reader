from __future__ import annotations

import csv
from datetime import (
    date,
    timedelta,
)
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...services.passage_edit_service import (
    PassageEditService,
)
from ...services.passage_query_service import PassageQueryService
from ..models.passage_table_model import PassageTableModel
from ..widgets.passage_datetime_filter import (
    PassageDateTimeFilter,
)
from .passage_edit_dialog import (
    PassageEditDialog,
)

CSV_FIELDS = (
    "passage_uuid",
    "observed_at",
    "tax_code",
    "common_name",
    "individual_count",
    "direction",
    "confidence",
    "needs_review",
    "length_mm",
    "glass_position",
    "comment",
    "video_file_name",
    "frame_number",
    "position_ms",
)


class PassageListDialog(QDialog):
    passage_open_requested = Signal(int, int)
    passages_changed = Signal(int)

    def __init__(
        self,
        database_path: Path,
        station_id: int,
        current_day: date | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.database_path = database_path
        self.station_id = station_id
        self.service = PassageQueryService()
        self.setWindowTitle("Passages")
        self.resize(1220, 680)
        self.setModal(False)
        self.edit_service = PassageEditService()

        title = QLabel("Passages enregistrés")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.datetime_filter = PassageDateTimeFilter(current_day)

        self.datetime_filter.refresh_requested.connect(self.reload)
        edit_button = QPushButton("Modifier…")
        delete_button = QPushButton("Supprimer")
        open_button = QPushButton("Afficher dans le lecteur")
        export_button = QPushButton("Exporter CSV…")

        filters = QHBoxLayout()
        filters.addWidget(
            self.datetime_filter,
            stretch=1,
        )

        filters.addStretch()
        filters.addWidget(open_button)
        filters.addWidget(edit_button)
        filters.addWidget(export_button)
        filters.addWidget(delete_button)

        self.model = PassageTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.count_label = QLabel()

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(filters)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.count_label)

        delete_button.clicked.connect(self._delete_selected)
        open_button.clicked.connect(self._open_selected)
        edit_button.clicked.connect(self._edit_selected)
        export_button.clicked.connect(self._export_csv)
        self.table.doubleClicked.connect(lambda _index: self._edit_selected())
        self.reload()

    def reload(self) -> None:
        start_at, end_at = self.datetime_filter.period()

        if end_at <= start_at:
            QMessageBox.warning(
                self,
                "Période invalide",
                ("La date et l'heure de fin doivent être postérieures au début."),
            )
            return

        rows = self.service.list_for_period(
            self.database_path,
            self.station_id,
            start_at,
            end_at,
        )

        self.model.set_rows(rows)

        self.count_label.setText(f"{len(rows)} passage(s)")

        self.table.resizeColumnsToContents()

    def _selected_row(self) -> dict[str, object] | None:
        index = self.table.currentIndex()
        return self.model.row_at(index.row()) if index.isValid() else None

    def _open_selected(self) -> None:
        rows = self._selected_rows()

        if len(rows) != 1:
            QMessageBox.information(
                self,
                "Sélection invalide",
                "Sélectionnez exactement un passage à afficher dans le lecteur.",
            )
            return

        row = rows[0]

        self.passage_open_requested.emit(
            int(row["video_part_id"]),
            int(row["frame_number"]),
        )

    def _delete_selected(self) -> None:
        rows = self._selected_rows()

        if not rows:
            QMessageBox.information(
                self,
                "Aucun passage sélectionné",
                "Sélectionnez au moins un passage à supprimer.",
            )
            return

        if len(rows) == 1:
            row = rows[0]

            question = f"Supprimer le passage {row['tax_code']} du {row['observed_at']} ?"
        else:
            question = f"Supprimer définitivement les {len(rows)} passages sélectionnés ?"

        answer = QMessageBox.question(
            self,
            "Supprimer les passages",
            question,
            (QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        passage_ids = [int(row["id"]) for row in rows]

        try:
            video_part_ids = self.service.delete_many(
                self.database_path,
                passage_ids,
            )

        except (
            ValueError,
            OSError,
            RuntimeError,
        ) as error:
            QMessageBox.critical(
                self,
                "Suppression impossible",
                str(error),
            )
            return

        self.reload()

        for video_part_id in video_part_ids:
            self.passages_changed.emit(video_part_id)

        self.count_label.setText(f"{len(rows)} passage(s) supprimé(s)")

    def _export_csv(self) -> None:
        row_count = self.model.rowCount()

        if row_count == 0:
            QMessageBox.information(
                self,
                "Aucun passage",
                "Aucun passage n'est disponible pour la période sélectionnée.",
            )
            return

        start_at, end_at = self.datetime_filter.period()

        end_inclusive = end_at - timedelta(minutes=1)

        default_name = f"passages_{start_at:%Y-%m-%d_%H-%M}_au_{end_inclusive:%Y-%m-%d_%H-%M}.csv"

        selected_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exporter les passages",
            default_name,
            ("Fichiers CSV (*.csv);;Tous les fichiers (*)"),
        )

        if not selected_path:
            return

        output_path = Path(selected_path)

        if output_path.suffix.lower() != ".csv":
            output_path = output_path.with_suffix(".csv")

        try:
            with output_path.open(
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=CSV_FIELDS,
                    delimiter=";",
                )

                writer.writeheader()

                for row_index in range(row_count):
                    row = self.model.row_at(row_index)

                    if row is None:
                        continue

                    writer.writerow(
                        {
                            "passage_uuid": row["passage_uuid"],
                            "observed_at": row["observed_at"],
                            "tax_code": row["tax_code"],
                            "common_name": row["common_name"],
                            "individual_count": row["individual_count"],
                            "direction": row["direction"],
                            "confidence": row["confidence"],
                            "needs_review": int(bool(row["needs_review"])),
                            "length_mm": (row["length_mm"] if row["length_mm"] is not None else ""),
                            "glass_position": row["glass_position"],
                            "comment": (row["comment"] or ""),
                            "video_file_name": row["video_file_name"],
                            "frame_number": row["frame_number"],
                            "position_ms": row["position_ms"],
                        }
                    )

        except OSError as error:
            QMessageBox.critical(
                self,
                "Export impossible",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "Export terminé",
            (f"{row_count} passage(s) ont été exportés dans :\n\n{output_path}"),
        )

    def _edit_selected(self) -> None:
        rows = self._selected_rows()

        if len(rows) != 1:
            QMessageBox.information(
                self,
                "Sélection invalide",
                "Sélectionnez exactement un passage à modifier.",
            )
            return

        row = rows[0]

        if row is None:
            return

        try:
            passage = self.edit_service.get_for_edit(
                self.database_path,
                int(row["id"]),
            )

            taxa = self.edit_service.list_taxa(self.database_path)

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Passage introuvable",
                str(error),
            )
            return

        dialog = PassageEditDialog(
            passage,
            taxa,
            self,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            self.edit_service.update(
                self.database_path,
                int(row["id"]),
                dialog.value(),
                measurement_method=str(passage["measurement_method"]),
                original_glass_position=str(passage["glass_position"]),
            )

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Modification impossible",
                str(error),
            )
            return

        self.reload()

        self.passages_changed.emit(int(row["video_part_id"]))

    def _selected_rows(
        self,
    ) -> list[dict[str, object]]:
        selected_indexes = self.table.selectionModel().selectedRows()

        rows: list[dict[str, object]] = []

        for index in selected_indexes:
            row = self.model.row_at(index.row())

            if row is not None:
                rows.append(row)

        return rows
