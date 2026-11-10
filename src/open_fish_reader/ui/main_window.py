from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Slot
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QToolBar

from ..core.exceptions import OpenFishReaderError
from ..domain.indexed_video_part import IndexedVideoPart
from ..services.playback_queue_service import PlaybackQueueService
from ..services.station_service import OpenedStation, StationService
from ..version import APP_NAME, APP_VERSION
from ..video.frame import DecodedFrame
from ..video.playback_controller import PlaybackController
from .dialogs.day_selection_dialog import DaySelectionDialog
from .dialogs.indexing_progress_dialog import IndexingProgressDialog
from .widgets.reader_widget import ReaderWidget
from .workers.day_indexing_worker import DayIndexingWorker
from .workers.frame_sequence_worker import FrameSequenceWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self._opened_station: OpenedStation | None = None
        self._station_service = StationService()
        self._playback_queue_service = PlaybackQueueService()
        self._decoded_frames: list[DecodedFrame] = []
        self._current_frame_index = -1

        self._indexing_thread: QThread | None = None
        self._indexing_worker: DayIndexingWorker | None = None
        self._progress_dialog: IndexingProgressDialog | None = None

        self._frame_thread: QThread | None = None

        self._current_day_folder: Path | None = None
        self._video_parts: list[IndexedVideoPart] = []
        self._current_part_index = -1

        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.resize(1200, 800)

        self.reader_widget = ReaderWidget()
        self.setCentralWidget(self.reader_widget)
        self._playback = PlaybackController(self)
        self._playback.frame_changed.connect(self._playback_frame_changed)
        self._playback.playing_changed.connect(self._playback_state_changed)
        self._playback.speed_changed.connect(self._playback_speed_changed)
        self._playback.sequence_finished.connect(self._playback_sequence_finished)

        self.reader_widget.play_pause_button.clicked.connect(self._playback.toggle)
        self.reader_widget.speed_control.decrease_requested.connect(self._playback.decrease_speed)
        self.reader_widget.speed_control.increase_requested.connect(self._playback.increase_speed)
        self.reader_widget.speed_control.reset_requested.connect(self._playback.reset_speed)

        self._pending_auto_play = False

        self.reader_widget.previous_file_button.clicked.connect(self._open_previous_file)
        self.reader_widget.next_file_button.clicked.connect(self._open_next_file)
        self.reader_widget.previous_frame_button.clicked.connect(self._show_previous_frame)
        self.reader_widget.next_frame_button.clicked.connect(self._show_next_frame)

        toolbar = QToolBar("Principal", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addAction("Ouvrir une station", self.open_station)
        self.day_action = toolbar.addAction(
            "Choisir une journée",
            self.choose_day,
        )
        self.day_action.setEnabled(False)
        toolbar.addSeparator()
        toolbar.addAction("Quitter", self.close)
        self.statusBar().showMessage("Prêt")

    def open_station(self) -> None:
        selected_folder = QFileDialog.getExistingDirectory(
            self,
            "Ouvrir le dossier d'une station",
        )
        if not selected_folder:
            return

        try:
            opened_station = self._station_service.open_station(Path(selected_folder))
        except (OpenFishReaderError, OSError, ValueError) as error:
            QMessageBox.critical(self, "Station invalide", str(error))
            return

        self._stop_frame_worker()
        self._close_opened_station()
        self._opened_station = opened_station
        self._video_parts = []
        self._current_part_index = -1
        self._current_day_folder = None

        self.reader_widget.station_label.setText(f"Station : {opened_station.station.name}")
        self.reader_widget.day_label.setText("Journée : -")
        self.reader_widget.clear_video_information()
        self.reader_widget.set_navigation_enabled(False, False)
        self.day_action.setEnabled(True)
        self.statusBar().showMessage(f"Station ouverte : {opened_station.station.name}")
        self.choose_day()

    def choose_day(self) -> None:
        if self._opened_station is None:
            return

        rows = self._opened_station.connection.execute(
            """
            SELECT day_date, event_count, video_part_count
            FROM days
            ORDER BY day_date
            """
        ).fetchall()
        indexed_days = {
            str(row["day_date"]): (
                int(row["event_count"]),
                int(row["video_part_count"]),
            )
            for row in rows
        }

        dialog = DaySelectionDialog(
            self._opened_station.day_folders,
            indexed_days,
            self,
        )
        dialog.day_selected.connect(self._start_day_indexing)
        dialog.exec()

    def _start_day_indexing(
        self,
        day_folder: Path,
        force: bool,
    ) -> None:
        if self._opened_station is None or self._indexing_thread is not None:
            return

        self._current_day_folder = day_folder
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
        self._indexing_worker.completed.connect(self._day_indexed)
        self._indexing_worker.failed.connect(self._indexing_failed)
        self._indexing_worker.cancelled.connect(self._indexing_cancelled)
        self._indexing_worker.finished.connect(self._indexing_thread.quit)
        self._indexing_worker.finished.connect(self._indexing_worker.deleteLater)
        self._indexing_thread.finished.connect(self._indexing_finished)
        self._progress_dialog.cancel_button.clicked.connect(self._indexing_worker.cancel)

        self._progress_dialog.show()
        self._indexing_thread.start()

    @Slot(int, int, int, bool)
    def _day_indexed(
        self,
        event_count: int,
        part_count: int,
        duration_ms: int,
        skipped: bool,
    ) -> None:
        if self._opened_station is None or self._current_day_folder is None:
            return

        day_folder = self._current_day_folder

        self.reader_widget.day_label.setText(f"Journée : {day_folder.name}")

        self._video_parts = self._playback_queue_service.load_day(
            self._opened_station.database_path,
            self._opened_station.station.source_folder,
            day_folder.name,
        )
        self._current_part_index = -1

        if skipped:
            state = "Journée inchangée, index SQLite réutilisé."
        else:
            state = "Index différentiel mis à jour."

        self.statusBar().showMessage(
            f"{state} {event_count} événements, {part_count} parties, {duration_ms / 1000:.3f} s."
        )

        if not self._video_parts:
            self.reader_widget.clear_video_information()
            self.reader_widget.set_navigation_enabled(
                False,
                False,
            )
            QMessageBox.information(
                self,
                "Journée vide",
                "Aucune partie vidéo n'est disponible pour cette journée.",
            )
            return

        self._open_part(0)

    @Slot(str)
    def _indexing_failed(
        self,
        message: str,
    ) -> None:
        QMessageBox.critical(
            self,
            "Erreur d'indexation",
            message,
        )
        self.statusBar().showMessage("Échec de l'indexation")

    @Slot()
    def _indexing_cancelled(self) -> None:
        self.statusBar().showMessage("Indexation annulée")

    @Slot()
    def _indexing_finished(self) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.close()

        if self._indexing_thread is not None:
            self._indexing_thread.deleteLater()

        self._progress_dialog = None
        self._indexing_thread = None
        self._indexing_worker = None

    def _open_previous_file(self) -> None:
        if self._current_part_index <= 0:
            return

        was_playing = self._playback.is_playing
        self._pending_auto_play = was_playing

        self._open_part(self._current_part_index - 1)

    def _open_next_file(self) -> None:
        if self._current_part_index + 1 >= len(self._video_parts):
            return

        was_playing = self._playback.is_playing
        self._pending_auto_play = was_playing

        self._open_part(self._current_part_index + 1)

    def _open_part(self, index: int) -> None:
        if self._frame_thread is not None:
            return

        if index < 0 or index >= len(self._video_parts):
            return

        self._playback.pause()

        self._current_part_index = index
        part = self._video_parts[index]

        self._decoded_frames = []
        self._current_frame_index = -1

        self.reader_widget.file_label.setText(f"Fichier : {part.video_path.name}")
        self.reader_widget.event_label.setText(f"Événement : {part.source_event_id}")
        self.reader_widget.part_label.setText(
            f"Partie : {part.part_number}    Fichier {index + 1}/{len(self._video_parts)}"
        )
        self.reader_widget.frame_label.setText("Image : chargement...")
        self.reader_widget.timestamp_label.setText("Horodatage : chargement...")

        self.reader_widget.set_file_navigation_enabled(
            False,
            False,
        )
        self.reader_widget.set_frame_navigation_enabled(
            False,
            False,
        )
        self.reader_widget.play_pause_button.setEnabled(False)

        self.statusBar().showMessage(f"Décodage de {part.video_path.name}...")

        self._frame_thread = QThread(self)
        self._frame_worker = FrameSequenceWorker(part)

        self._frame_worker.moveToThread(self._frame_thread)
        self._frame_thread.started.connect(self._frame_worker.run)
        self._frame_worker.completed.connect(self._frame_sequence_ready)
        self._frame_worker.failed.connect(self._first_frame_failed)
        self._frame_worker.finished.connect(self._frame_thread.quit)
        self._frame_worker.finished.connect(self._frame_worker.deleteLater)
        self._frame_thread.finished.connect(self._frame_worker_finished)

        self._frame_thread.start()

    @Slot(object)
    def _frame_sequence_ready(
        self,
        frames: list[DecodedFrame],
    ) -> None:
        self._decoded_frames = frames

        if self._current_part_index < 0 or self._current_part_index >= len(self._video_parts):
            return

        part = self._video_parts[self._current_part_index]

        self._playback.load_sequence(
            frame_count=len(frames),
            fps=part.recording_fps,
        )

        self.reader_widget.play_pause_button.setEnabled(len(frames) > 1)

        if self._pending_auto_play:
            self._pending_auto_play = False
            self._playback.play()

    def _show_previous_frame(self) -> None:
        if self._playback.is_playing:
            return
        self._playback.set_current_index(self._current_frame_index - 1)

    def _show_next_frame(self) -> None:
        if self._playback.is_playing:
            return
        self._playback.set_current_index(self._current_frame_index + 1)

    def _display_current_frame(self) -> None:
        if (
            self._current_frame_index < 0
            or self._current_frame_index >= len(self._decoded_frames)
            or self._current_part_index < 0
            or self._current_part_index >= len(self._video_parts)
        ):
            return

        frame = self._decoded_frames[self._current_frame_index]
        part = self._video_parts[self._current_part_index]
        timestamp = frame.absolute_timestamp.isoformat(timespec="milliseconds")

        self.reader_widget.video_widget.set_image(frame.image)
        self.reader_widget.frame_label.setText(
            f"Image : {self._current_frame_index + 1}/{len(self._decoded_frames)}"
        )
        self.reader_widget.timestamp_label.setText(f"Horodatage : {timestamp}")
        self.reader_widget.set_frame_navigation_enabled(
            has_previous_frame=self._current_frame_index > 0,
            has_next_frame=(self._current_frame_index + 1 < len(self._decoded_frames)),
        )
        self.statusBar().showMessage(
            f"{part.video_path.name} - "
            f"image {self._current_frame_index + 1}/"
            f"{len(self._decoded_frames)}"
        )

    @Slot(str)
    def _first_frame_failed(
        self,
        message: str,
    ) -> None:
        self.reader_widget.video_widget.clear()
        self.reader_widget.frame_label.setText("Image : erreur")
        self.reader_widget.timestamp_label.setText("Horodatage : -")
        self._decoded_frames = []
        self._current_frame_index = -1
        self.reader_widget.set_frame_navigation_enabled(False, False)
        QMessageBox.critical(
            self,
            "Erreur vidéo",
            message,
        )
        self.statusBar().showMessage("Échec du décodage vidéo")

    @Slot()
    def _frame_worker_finished(self) -> None:
        if self._frame_thread is not None:
            self._frame_thread.deleteLater()

        self._frame_thread = None
        self._frame_worker = None

        self._update_file_navigation()

    def _update_file_navigation(self) -> None:
        self.reader_widget.set_navigation_enabled(
            has_previous_file=self._current_part_index > 0,
            has_next_file=(self._current_part_index + 1 < len(self._video_parts)),
        )

    def _indexing_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Erreur d'indexation", message)
        self.statusBar().showMessage("Échec de l'indexation")

    def _indexing_finished(self) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.close()
        if self._indexing_thread is not None:
            self._indexing_thread.deleteLater()
        self._progress_dialog = None
        self._indexing_thread = None
        self._indexing_worker = None

    def _stop_frame_worker(self) -> None:
        if self._frame_thread is None:
            return
        self._frame_thread.quit()
        self._frame_thread.wait(3000)
        self._frame_thread = None
        self._frame_worker = None

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
        self._stop_frame_worker()
        self._close_opened_station()
        super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Left:
            self._show_previous_frame()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Right:
            self._show_next_frame()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Up:
            self._open_previous_file()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Down:
            self._open_next_file()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Space:
            self._playback.toggle()
            event.accept()
            return

        if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._playback.increase_speed()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Minus:
            self._playback.decrease_speed()
            event.accept()
            return

        super().keyPressEvent(event)

    @Slot(int)
    def _playback_frame_changed(self, index: int) -> None:
        self._current_frame_index = index
        self._display_current_frame()

    @Slot(bool)
    def _playback_state_changed(self, playing: bool) -> None:
        self.reader_widget.play_pause_button.setText("Pause" if playing else "Lecture")
        self.reader_widget.set_frame_navigation_enabled(
            has_previous_frame=(not playing and self._current_frame_index > 0),
            has_next_frame=(
                not playing and self._current_frame_index + 1 < len(self._decoded_frames)
            ),
        )

    @Slot(float)
    def _playback_speed_changed(self, speed: float) -> None:
        self.reader_widget.speed_control.set_speed(speed)

    @Slot()
    def _playback_sequence_finished(self) -> None:
        next_index = self._current_part_index + 1

        if next_index >= len(self._video_parts):
            self._pending_auto_play = False
            self.statusBar().showMessage("Fin de la journée")
            return

        self._pending_auto_play = True
        self._open_part(next_index)
