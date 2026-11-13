from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QStyledItemDelegate


class TaxonShortcutDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setMaxLength(1)
        editor.setPlaceholderText("A-Z / 0-9")
        return editor

    def setEditorData(self, editor, index) -> None:
        editor.setText(str(index.data() or ""))
        editor.selectAll()

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.text())
