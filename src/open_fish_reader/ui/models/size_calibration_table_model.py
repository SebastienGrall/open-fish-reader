from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from ...domain.size_calibration import SizeCalibration


class SizeCalibrationTableModel(QAbstractTableModel):
    HEADERS = (
        "Début de validité",
        "Fin de validité",
        "Proche (mm/px)",
        "Milieu (mm/px)",
        "Loin (mm/px)",
        "Commentaire",
        "État",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[SizeCalibration] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._items)

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
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return item
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        values = (
            item.valid_from.astimezone().strftime("%d/%m/%Y %H:%M:%S"),
            (
                item.valid_to.astimezone().strftime("%d/%m/%Y %H:%M:%S")
                if item.valid_to is not None
                else "En cours"
            ),
            f"{item.near_mm_per_pixel:.6f}",
            f"{item.middle_mm_per_pixel:.6f}",
            f"{item.far_mm_per_pixel:.6f}",
            item.comment or "",
            "Active" if item.is_active else "Clôturée",
        )
        return values[index.column()]

    def set_items(self, items: list[SizeCalibration]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def item_at(self, row: int) -> SizeCalibration | None:
        return self._items[row] if 0 <= row < len(self._items) else None
