from __future__ import annotations

import csv
from datetime import date, datetime, time, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
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

from ...services.passage_query_service import PassageQueryService
from ..models.passage_table_model import PassageTableModel

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

        title = QLabel("Passages enregistrés")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        selected_day = current_day or datetime.now().date()
        self.start_date = QDateEdit(QDate(selected_day.year, selected_day.month, selected_day.day))
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit(QDate(selected_day.year, selected_day.month, selected_day.day))
        self.end_date.setCalendarPopup(True)
        refresh_button = QPushButton("Actualiser")
        delete_button = QPushButton("Supprimer")
        open_button = QPushButton("Afficher dans le lecteur")
        export_button = QPushButton("Exporter CSV…")

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Du"))
        filters.addWidget(self.start_date)
        filters.addWidget(QLabel("Au"))
        filters.addWidget(self.end_date)
        filters.addWidget(refresh_button)
        filters.addStretch()
        filters.addWidget(open_button)
        filters.addWidget(export_button)
        filters.addWidget(delete_button)

        export_button.clicked.connect(self._export_csv)

        self.model = PassageTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setWordWrap(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.count_label = QLabel()

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(filters)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.count_label)

        refresh_button.clicked.connect(self.reload)
        delete_button.clicked.connect(self._delete_selected)
        open_button.clicked.connect(self._open_selected)
        self.table.doubleClicked.connect(lambda _index: self._open_selected())
        self.reload()

    def reload(self) -> None:
        start_day = self.start_date.date().toPython()
        end_day = self.end_date.date().toPython()
        if end_day < start_day:
            QMessageBox.warning(
                self, "Période invalide", "La date de fin précède la date de début."
            )
            return
        timezone = datetime.now().astimezone().tzinfo
        start_at = datetime.combine(start_day, time.min, timezone)
        end_at = datetime.combine(end_day + timedelta(days=1), time.min, timezone)
        rows = self.service.list_for_period(self.database_path, self.station_id, start_at, end_at)
        self.model.set_rows(rows)
        self.count_label.setText(f"{len(rows)} passage(s)")
        self.table.resizeColumnsToContents()

    def _selected_row(self) -> dict[str, object] | None:
        index = self.table.currentIndex()
        return self.model.row_at(index.row()) if index.isValid() else None

    def _open_selected(self) -> None:
        row = self._selected_row()
        if row is not None:
            self.passage_open_requested.emit(int(row["video_part_id"]), int(row["frame_number"]))

    def _delete_selected(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        answer = QMessageBox.question(
            self,
            "Supprimer le passage",
            f"Supprimer le passage {row['tax_code']} du {row['observed_at']} ?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        video_part_id = self.service.delete(
            self.database_path,
            int(row["id"]),
        )

        self.reload()

        if video_part_id is not None:
            self.passages_changed.emit(video_part_id)

    def _export_csv(self) -> None:
        row_count = self.model.rowCount()

        if row_count == 0:
            QMessageBox.information(
                self,
                "Aucun passage",
                "Aucun passage n'est disponible pour la période sélectionnée.",
            )
            return

        start_text = self.start_date.date().toString("yyyy-MM-dd")
        end_text = self.end_date.date().toString("yyyy-MM-dd")

        default_name = f"passages_{start_text}_au_{end_text}.csv"

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
