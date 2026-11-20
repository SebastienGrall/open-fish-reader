from __future__ import annotations

import platform
import sqlite3
from datetime import datetime

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QGuiApplication,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.resources import resource_path
from ...domain.database_information import DatabaseInformation
from ...version import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    COPYRIGHT,
    DEVELOPERS,
    LICENSE_NAME,
    ORGANIZATION_NAME,
)


class AboutDialog(QDialog):
    def __init__(
        self,
        database_information: DatabaseInformation | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(f"À propos de {APP_NAME}")
        self.resize(650, 650)

        self._text = self._build_text(database_information)

        # Logo
        logo_label = QLabel()

        logo = QPixmap(str(resource_path("icons/open_fish_reader_256.png")))

        if not logo.isNull():
            logo_label.setPixmap(
                logo.scaled(
                    128,
                    128,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Nom du logiciel
        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Version
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: palette(mid);")

        # Organisme et crédits
        developers_text = ", ".join(DEVELOPERS)

        credits = QLabel(
            f"<b>{APP_DESCRIPTION}</b>"
            "<br><br>"
            f"{ORGANIZATION_NAME}<br>"
            f"Développement : {developers_text}<br>"
            f"{COPYRIGHT}<br>"
            f"Licence : {LICENSE_NAME}"
        )
        credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits.setWordWrap(True)
        credits.setTextFormat(Qt.TextFormat.RichText)

        # Informations techniques et base ouverte
        details = QTextEdit()
        details.setReadOnly(True)
        details.setPlainText(self._text)
        details.setMinimumHeight(210)

        # Actions
        copy_button = QPushButton("Copier les informations")
        copy_button.clicked.connect(self._copy)
        license_button = QPushButton("Afficher la licence…")
        license_button.clicked.connect(self._show_license)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(copy_button)
        actions_layout.addWidget(license_button)
        actions_layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        # Mise en page
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            20,
            16,
            20,
            16,
        )
        layout.setSpacing(10)

        layout.addWidget(logo_label)
        layout.addWidget(title)
        layout.addWidget(version_label)
        layout.addWidget(credits)
        layout.addSpacing(8)
        layout.addWidget(
            details,
            stretch=1,
        )
        layout.addLayout(actions_layout)
        layout.addWidget(buttons)

    @staticmethod
    def _format_iso(value: str) -> str:
        try:
            return datetime.fromisoformat(value).astimezone().strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            return value

    @classmethod
    def _build_text(cls, database: DatabaseInformation | None) -> str:
        developers_text = ", ".join(DEVELOPERS)

        lines = [
            "LOGICIEL",
            f"Nom : {APP_NAME}",
            f"Version : {APP_VERSION}",
            f"Description : {APP_DESCRIPTION}",
            f"Organisme : {ORGANIZATION_NAME}",
            f"Développement : {developers_text}",
            f"Copyright : {COPYRIGHT}",
            f"Licence : {LICENSE_NAME}",
            "",
            "ENVIRONNEMENT",
            f"Python : {platform.python_version()}",
            f"PySide6 : {pyside_version}",
            f"SQLite : {sqlite3.sqlite_version}",
            (f"Système : {platform.system()} {platform.release()}"),
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

    def _show_license(self) -> None:
        license_path = resource_path("LICENSE")

        try:
            license_text = license_path.read_text(encoding="utf-8")
        except OSError as error:
            QMessageBox.warning(
                self,
                "Licence indisponible",
                (f"Le fichier de licence est introuvable :\n\n{license_path}\n\n{error}"),
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Licence du logiciel")
        dialog.resize(820, 650)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(license_text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)

        layout = QVBoxLayout(dialog)
        layout.addWidget(
            text,
            stretch=1,
        )
        layout.addWidget(buttons)

        dialog.exec()
