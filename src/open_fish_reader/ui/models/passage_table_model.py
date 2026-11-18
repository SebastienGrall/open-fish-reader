from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class PassageTableModel(QAbstractTableModel):
    HEADERS = (
        "Horodatage",
        "Code",
        "Nom commun",
        "Nombre",
        "Sens",
        "Confiance",
        "À revoir",
        "Taille (mm)",
        "Position vitre",
        "Commentaire",
        "Fichier",
        "Image",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, object]] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.HEADERS)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
            and 0 <= section < len(self.HEADERS)
        ):
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return row
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return None
        directions = {-1: "Dévalaison", 0: "Indéterminé", 1: "Montaison"}
        positions = {"near": "Proche", "middle": "Milieu", "far": "Loin"}
        values = (
            row["observed_at"],
            row["tax_code"],
            row["common_name"],
            row["individual_count"],
            directions[int(row["direction"])],
            row["confidence"],
            "Oui" if row["needs_review"] else "Non",
            row["length_mm"] if row["length_mm"] is not None else "NA",
            positions[str(row["glass_position"])],
            row["comment"] or "",
            row["video_file_name"],
            int(row["frame_number"]) + 1,
        )
        return values[index.column()]

    def set_rows(self, rows: list[dict[str, object]]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def row_at(self, row: int) -> dict[str, object] | None:
        return self._rows[row] if 0 <= row < len(self._rows) else None
