from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

_SHORTCUTS = (
    ("← / →", "Image précédente / suivante"),
    ("↑ / ↓", "Fichier précédent / suivant"),
    ("Espace", "Lecture / pause"),
    ("Ctrl++", "Augmenter la vitesse"),
    ("Ctrl+-", "Diminuer la vitesse"),
    ("+", "Enregistrer une montaison"),
    ("0", "Enregistrer un sens indéterminé"),
    ("−", "Enregistrer une dévalaison"),
    ("Touche du taxon", "Sélectionner le taxon configuré"),
    ("Ctrl+Z / Retour arrière", "Retirer le dernier point de mesure"),
    ("Entrée / double-clic", "Terminer la mesure"),
    ("Échap", "Annuler la mesure"),
    ("Ctrl+clic", "Sélectionner plusieurs passages séparés"),
    ("Maj+clic", "Sélectionner une plage de passages"),
    ("Ctrl+A", "Sélectionner tous les passages"),
)


class KeyboardShortcutsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Raccourcis clavier")
        self.resize(660, 540)

        table = QTableWidget(len(_SHORTCUTS), 2)
        table.setHorizontalHeaderLabels(("Raccourci", "Action"))
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setAlternatingRowColors(True)
        for row, (shortcut, action) in enumerate(_SHORTCUTS):
            table.setItem(row, 0, QTableWidgetItem(shortcut))
            table.setItem(row, 1, QTableWidgetItem(action))
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(table, stretch=1)
        layout.addWidget(buttons)
