from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel

from .taxon_table_model import TaxonColumns, TaxonTableModel


class TaxonFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._query = ""
        self._active_only = False
        self.setDynamicSortFilter(True)
        self.setSortCaseSensitivity(self.sortCaseSensitivity().CaseInsensitive)

    def set_query(self, query: str) -> None:
        self._query = query.strip().casefold()
        self.invalidateFilter()

    def set_active_only(self, active_only: bool) -> None:
        self._active_only = active_only
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        if not isinstance(model, TaxonTableModel):
            return True

        if self._active_only:
            item = model.editable_taxa()[source_row]
            if not item.is_active:
                return False

        if not self._query:
            return True

        columns = (
            TaxonColumns.CODE,
            TaxonColumns.COMMON_NAME,
            TaxonColumns.SCIENTIFIC_NAME,
            TaxonColumns.SANDRE,
            TaxonColumns.STAGE,
        )
        return any(
            self._query
            in str(model.data(model.index(source_row, column, source_parent)) or "").casefold()
            for column in columns
        )
