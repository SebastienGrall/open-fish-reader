from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from ..core.exceptions import OpenFishReaderError
from ..indexing.day_scanner import find_day_folders
from ..indexing.station_scanner import scan_station_identity
from ..version import APP_NAME, APP_VERSION


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.resize(1200, 800)

        self.label = QLabel(
            "Open Fish Reader\n\n"
            "Ouvrez le dossier d'une station.",
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

        try:
            station_folder = Path(selected_folder)
            station = scan_station_identity(station_folder)
            day_folders = find_day_folders(station_folder)

        except (OpenFishReaderError, OSError) as error:
            QMessageBox.critical(
                self,
                "Station invalide",
                str(error),
            )
            return

        self.label.setText(
            f"Station : {station.name}\n"
            f"Dossier : {station.source_folder}\n"
            f"Journées détectées : {len(day_folders)}\n\n"
            "Le socle fonctionne correctement."
        )

        self.statusBar().showMessage(
            f"Station ouverte : {station.name}"
        )