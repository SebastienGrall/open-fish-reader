from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox, QToolBar

from ..core.exceptions import OpenFishReaderError
from ..services.station_service import OpenedStation, StationService
from ..version import APP_NAME, APP_VERSION
from .dialogs.day_selection_dialog import DaySelectionDialog
from .dialogs.indexing_progress_dialog import IndexingProgressDialog
from .workers.day_indexing_worker import DayIndexingWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._opened_station: OpenedStation | None = None
        self._station_service = StationService()
        self._indexing_thread: QThread | None = None
        self._indexing_worker: DayIndexingWorker | None = None
        self._progress_dialog: IndexingProgressDialog | None = None
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
        toolbar.addAction("Ouvrir une station", self.open_station)
        self.day_action = toolbar.addAction("Choisir une journée", self.choose_day)
        self.day_action.setEnabled(False)
        toolbar.addSeparator()
        toolbar.addAction("Quitter", self.close)
        self.statusBar().showMessage("Prêt")

    def open_station(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Ouvrir le dossier d'une station")
        if not selected:
            return
        try:
            opened = self._station_service.open_station(Path(selected))
        except (OpenFishReaderError, OSError, ValueError) as error:
            QMessageBox.critical(self, "Station invalide", str(error))
            return
        self._close_opened_station()
        self._opened_station = opened
        self.day_action.setEnabled(True)
        self._show_station_summary()
        self.choose_day()

    def choose_day(self) -> None:
        if self._opened_station is None:
            return
        rows = self._opened_station.connection.execute(
            "SELECT day_date, event_count, video_part_count FROM days ORDER BY day_date"
        ).fetchall()
        indexed = {
            str(r["day_date"]): (int(r["event_count"]), int(r["video_part_count"])) for r in rows
        }
        dialog = DaySelectionDialog(self._opened_station.day_folders, indexed, self)
        dialog.day_selected.connect(self._start_day_indexing)
        dialog.exec()

    def _start_day_indexing(self, day_folder: Path, force: bool) -> None:
        if self._opened_station is None or self._indexing_thread is not None:
            return
        self._progress_dialog = IndexingProgressDialog(self)
        self._indexing_thread = QThread(self)
        self._indexing_worker = DayIndexingWorker(
            self._opened_station.database_path,
            self._opened_station.station.source_folder,
            day_folder,
            force,
        )
        self._indexing_worker.moveToThread(self._indexing_thread)
        self._indexing_thread.started.connect(self._indexing_worker.run)
        self._indexing_worker.progress.connect(self._progress_dialog.update_progress)
        self._indexing_worker.completed.connect(
            lambda events, parts, duration, skipped: self._day_indexed(
                day_folder, events, parts, duration, skipped
            )
        )
        self._indexing_worker.failed.connect(self._indexing_failed)
        self._indexing_worker.cancelled.connect(
            lambda: self.statusBar().showMessage("Indexation annulée")
        )
        self._indexing_worker.finished.connect(self._indexing_thread.quit)
        self._indexing_worker.finished.connect(self._indexing_worker.deleteLater)
        self._indexing_thread.finished.connect(self._indexing_finished)
        self._progress_dialog.cancel_button.clicked.connect(self._indexing_worker.cancel)
        self._progress_dialog.show()
        self._indexing_thread.start()

    def _day_indexed(
        self, day: Path, events: int, parts: int, duration_ms: int, skipped: bool
    ) -> None:
        state = (
            "Journée inchangée, index SQLite réutilisé."
            if skipped
            else "Index différentiel mis à jour."
        )
        self.label.setText(
            f"Journée : {day.name}\n\nÉvénements : {events}\n"
            f"Parties vidéo : {parts}\nDurée totale : {duration_ms / 1000:.3f} s\n\n{state}"
        )
        self.statusBar().showMessage(state)

    def _indexing_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Erreur d'indexation", message)

    def _indexing_finished(self) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.close()
        if self._indexing_thread is not None:
            self._indexing_thread.deleteLater()
        self._progress_dialog = None
        self._indexing_thread = None
        self._indexing_worker = None

    def _show_station_summary(self) -> None:
        if self._opened_station is None:
            return
        opened = self._opened_station
        self.label.setText(
            f"Station : {opened.station.name}\nDossier : {opened.station.source_folder}\n\n"
            f"Journées détectées : {opened.detected_day_count}\n\n"
            f"Base SQLite :\n{opened.database_path}"
        )

    def _close_opened_station(self) -> None:
        if self._opened_station is not None:
            self._opened_station.connection.close()
            self._opened_station = None

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._indexing_worker is not None:
            self._indexing_worker.cancel()
        if self._indexing_thread is not None:
            self._indexing_thread.quit()
            self._indexing_thread.wait(3000)
        self._close_opened_station()
        super().closeEvent(event)
