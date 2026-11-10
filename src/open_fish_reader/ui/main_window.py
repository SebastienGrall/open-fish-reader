from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from ..core.exceptions import OpenFishReaderError
from ..services.station_service import OpenedStation, StationService
from ..version import APP_NAME, APP_VERSION


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self._opened_station: OpenedStation | None = None
        self._station_service = StationService()

        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.resize(1200, 800)

        self.label = QLabel(
            "Open Fish Reader\n\nOuvrez le dossier d'une station.",
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        self.setCentralWidget(self.label)

        toolbar = QToolBar("Principal", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(
            "Ouvrir une station",
            self.open_station,
        )
        toolbar.addSeparator()
        toolbar.addAction(
            "Quitter",
            self.close,
        )

        self.statusBar().showMessage("Prêt")

    def open_station(self) -> None:
        selected_folder = QFileDialog.getExistingDirectory(
            self,
            "Ouvrir le dossier d'une station",
        )

        if not selected_folder:
            return

        self.statusBar().showMessage("Indexation de la station en cours...")

        try:
            opened_station = self._station_service.open_station(Path(selected_folder))

        except (OpenFishReaderError, OSError, ValueError) as error:
            QMessageBox.critical(
                self,
                "Station invalide",
                str(error),
            )
            self.statusBar().showMessage("Échec de l'ouverture")
            return

        self._close_opened_station()
        self._opened_station = opened_station

        self.label.setText(
            f"Station : {opened_station.station.name}\n"
            f"Dossier : {opened_station.station.source_folder}\n\n"
            f"Journées détectées : "
            f"{opened_station.detected_day_count}\n\n"
            "Base SQLite :\n"
            f"{opened_station.database_path}\n\n"
            "La station est prête.\n"
            "La prochaine étape sera la sélection "
            "et l'indexation d'une journée."
        )

        self.statusBar().showMessage(f"Station ouverte : {opened_station.station.name}")

    def _close_opened_station(self) -> None:
        if self._opened_station is None:
            return

        self._opened_station.connection.close()
        self._opened_station = None

    def closeEvent(self, event: QCloseEvent) -> None:
        self._close_opened_station()
        super().closeEvent(event)
