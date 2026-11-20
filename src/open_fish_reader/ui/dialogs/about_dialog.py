from __future__ import annotations

import platform
import sqlite3
from datetime import datetime

from PySide6 import __version__ as pyside_version
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...domain.database_information import DatabaseInformation
from ...version import APP_NAME, APP_VERSION


class AboutDialog(QDialog):
    def __init__(
        self,
        database_information: DatabaseInformation | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"À propos de {APP_NAME}")
        self.resize(650, 470)
        self._text = self._build_text(database_information)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        subtitle = QLabel("Dépouillement vidéo et saisie des passages piscicoles")
        subtitle.setWordWrap(True)
        details = QTextEdit()
        details.setReadOnly(True)
        details.setPlainText(self._text)

        copy_button = QPushButton("Copier les informations")
        copy_button.clicked.connect(self._copy)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(details, stretch=1)
        layout.addWidget(copy_button)
        layout.addWidget(buttons)

    @staticmethod
    def _format_iso(value: str) -> str:
        try:
            return datetime.fromisoformat(value).astimezone().strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            return value

    @classmethod
    def _build_text(cls, database: DatabaseInformation | None) -> str:
        lines = [
            "LOGICIEL",
            f"Version {APP_NAME} : {APP_VERSION}",
            f"Python : {platform.python_version()}",
            f"PySide6 : {pyside_version}",
            f"SQLite : {sqlite3.sqlite_version}",
            f"Système : {platform.system()} {platform.release()}",
        ]
        if database is None:
            lines.extend(["", "BASE DE LA STATION", "Aucune station ouverte."])
        else:
            lines.extend(
                [
                    "",
                    "BASE DE LA STATION",
                    f"Schéma SQLite : {database.schema_version}",
                    f"Créée avec : {database.created_with_app_version}",
                    f"Dernière ouverture avec : {database.last_opened_with_app_version}",
                    f"Créée le : {cls._format_iso(database.created_at)}",
                    f"Dernière mise à jour : {cls._format_iso(database.updated_at)}",
                    f"Fichier : {database.database_path}",
                ]
            )
        return "\n".join(lines)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._text)
        QMessageBox.information(
            self,
            "Informations copiées",
            "Les informations ont été copiées dans le presse-papiers.",
        )
