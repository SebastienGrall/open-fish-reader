from __future__ import annotations

from dataclasses import dataclass, replace

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal

from ...domain.taxon import Taxon


@dataclass(frozen=True, slots=True)
class EditableTaxon:
    id: int
    tax_code: str
    stage_code: str | None
    stage_label: str | None
    common_name: str
    sandre_code: str | None
    scientific_name: str
    is_active: bool
    keyboard_shortcut: str | None
    display_order: int

    @classmethod
    def from_taxon(cls, taxon: Taxon) -> EditableTaxon:
        return cls(
            id=taxon.id,
            tax_code=taxon.tax_code,
            stage_code=taxon.stage_code,
            stage_label=taxon.stage_label,
            common_name=taxon.common_name,
            sandre_code=taxon.sandre_code,
            scientific_name=taxon.scientific_name,
            is_active=taxon.is_active,
            keyboard_shortcut=taxon.keyboard_shortcut,
            display_order=taxon.display_order,
        )


class TaxonColumns:
    ACTIVE = 0
    ORDER = 1
    CODE = 2
    COMMON_NAME = 3
    STAGE = 4
    STAGE_CODE = 5
    SANDRE = 6
    SCIENTIFIC_NAME = 7
    SHORTCUT = 8
    COUNT = 9


_HEADERS = (
    "Actif",
    "Ordre",
    "Code",
    "Nom commun",
    "Stade",
    "Code stade",
    "SANDRE",
    "Nom scientifique",
    "Raccourci",
)


class TaxonTableModel(QAbstractTableModel):
    validation_changed = Signal(bool, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[EditableTaxon] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self._items)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else TaxonColumns.COUNT

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
            and 0 <= section < len(_HEADERS)
        ):
            return _HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        if index.column() == TaxonColumns.ACTIVE and role == Qt.ItemDataRole.CheckStateRole:
            return Qt.CheckState.Checked if item.is_active else Qt.CheckState.Unchecked
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            values = (
                "",
                item.display_order,
                item.tax_code,
                item.common_name,
                item.stage_label or "Aucun stade",
                item.stage_code or "",
                item.sandre_code or "",
                item.scientific_name,
                item.keyboard_shortcut or "",
            )
            return values[index.column()]
        if role == Qt.ItemDataRole.ToolTipRole:
            stage = (
                f"Stade {item.stage_code} : {item.stage_label}"
                if item.stage_code and item.stage_label
                else "Aucun stade"
            )
            return f"{item.tax_code} — {item.common_name}\n{item.scientific_name}\n{stage}"
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == TaxonColumns.ACTIVE:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        elif index.column() in (TaxonColumns.ORDER, TaxonColumns.SHORTCUT):
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return False
        item = self._items[index.row()]
        if index.column() == TaxonColumns.ACTIVE and role == Qt.ItemDataRole.CheckStateRole:
            self._items[index.row()] = replace(item, is_active=value == Qt.CheckState.Checked.value)
        elif index.column() == TaxonColumns.ORDER and role == Qt.ItemDataRole.EditRole:
            try:
                order = max(0, int(value))
            except (TypeError, ValueError):
                return False
            self._items[index.row()] = replace(item, display_order=order)
        elif index.column() == TaxonColumns.SHORTCUT and role == Qt.ItemDataRole.EditRole:
            self._items[index.row()] = replace(
                item, keyboard_shortcut=normalize_shortcut(str(value))
            )
        else:
            return False
        self.dataChanged.emit(index, index, [role])
        self._validate()
        return True

    def set_taxa(self, taxa: list[Taxon]) -> None:
        self.beginResetModel()
        self._items = [EditableTaxon.from_taxon(taxon) for taxon in taxa]
        self.endResetModel()
        self._validate()

    def editable_taxa(self) -> tuple[EditableTaxon, ...]:
        return tuple(self._items)

    def active_count(self) -> int:
        return sum(item.is_active for item in self._items)

    def _validate(self) -> None:
        shortcuts: dict[str, str] = {}
        conflicts: list[str] = []
        for item in self._items:
            if not item.is_active or not item.keyboard_shortcut:
                continue
            if item.keyboard_shortcut in shortcuts:
                conflicts.append(
                    f"{item.keyboard_shortcut} ({shortcuts[item.keyboard_shortcut]} / {item.tax_code})"
                )
            else:
                shortcuts[item.keyboard_shortcut] = item.tax_code
        if conflicts:
            self.validation_changed.emit(False, "Raccourcis en conflit : " + ", ".join(conflicts))
        else:
            self.validation_changed.emit(True, "Configuration valide")


def normalize_shortcut(value: str) -> str | None:
    return value.strip().upper() or None
