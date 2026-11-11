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
from ..video.cache_policy import decide_full_cache
from ..video.frame import DecodedFrame
from ..video.playback_controller import PlaybackController
from .dialogs.day_selection_dialog import DaySelectionDialog
from .dialogs.indexing_progress_dialog import IndexingProgressDialog
from .widgets.reader_widget import ReaderWidget
from .workers.day_indexing_worker import DayIndexingWorker
from .workers.frame_sequence_worker import FrameSequenceWorker
from .workers.persistent_video_worker import PersistentVideoWorker


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
        self._frame_worker: FrameSequenceWorker | None = None

        self._persistent_thread: QThread | None = None
        self._persistent_worker: PersistentVideoWorker | None = None
        self._persistent_mode = False
        self._persistent_buffer_ready = False
        self._persistent_waiting_for_frame = False
        self._persistent_resume_after_frame = False

        self._current_day_folder: Path | None = None
        self._video_parts: list[IndexedVideoPart] = []
        self._current_part_index = -1
        self._pending_auto_play = False

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
        self.reader_widget.previous_file_button.clicked.connect(self._open_previous_file)
        self.reader_widget.next_file_button.clicked.connect(self._open_next_file)
        self.reader_widget.previous_frame_button.clicked.connect(self._show_previous_frame)
        self.reader_widget.next_frame_button.clicked.connect(self._show_next_frame)

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

        self._playback.pause()
        self._stop_persistent_worker()
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

    def _start_day_indexing(self, day_folder: Path, force: bool) -> None:
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
        state = (
            "Journée inchangée, index SQLite réutilisé."
            if skipped
            else "Index différentiel mis à jour."
        )
        self.statusBar().showMessage(
            f"{state} {event_count} événements, {part_count} parties, {duration_ms / 1000:.3f} s."
        )
        if not self._video_parts:
            self.reader_widget.clear_video_information()
            self.reader_widget.set_navigation_enabled(False, False)
            QMessageBox.information(
                self,
                "Journée vide",
                "Aucune partie vidéo n'est disponible pour cette journée.",
            )
            return
        self._open_part(0)

    @Slot(str)
    def _indexing_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Erreur d'indexation", message)
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
        self._pending_auto_play = self._playback.is_playing
        self._open_part(self._current_part_index - 1)

    def _open_next_file(self) -> None:
        if self._current_part_index + 1 >= len(self._video_parts):
            return
        self._pending_auto_play = self._playback.is_playing
        self._open_part(self._current_part_index + 1)

    def _open_part(self, index: int) -> None:
        if self._frame_thread is not None:
            return
        if index < 0 or index >= len(self._video_parts):
            return

        self._playback.pause()

        if not self._stop_persistent_worker():
            print("[MainWindow] Impossible d'ouvrir la vidéo suivante : worker encore actif")
            return
        self._current_part_index = index
        part = self._video_parts[index]
        self._decoded_frames = []
        self._current_frame_index = -1
        self._persistent_mode = False
        self._persistent_buffer_ready = False
        self._persistent_waiting_for_frame = False
        self._persistent_resume_after_frame = False

        self.reader_widget.file_label.setText(f"Fichier : {part.video_path.name}")
        self.reader_widget.event_label.setText(f"Événement : {part.source_event_id}")
        self.reader_widget.part_label.setText(
            f"Partie : {part.part_number}    Fichier {index + 1}/{len(self._video_parts)}"
        )
        self.reader_widget.frame_label.setText("Image : chargement...")
        self.reader_widget.timestamp_label.setText("Horodatage : chargement...")
        self.reader_widget.set_file_navigation_enabled(False, False)
        self.reader_widget.set_frame_navigation_enabled(False, False)
        self.reader_widget.play_pause_button.setEnabled(False)

        cache_decision = decide_full_cache(part)
        if cache_decision.allow_full_cache:
            self.statusBar().showMessage(f"Chargement en mémoire de {part.video_path.name}...")
            self._start_full_cache_loading(part)
            return

        self._persistent_mode = True
        self.statusBar().showMessage(f"Ouverture persistante de {part.video_path.name}...")
        self._start_persistent_loading(part)

    def _start_full_cache_loading(self, part: IndexedVideoPart) -> None:
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

    def _start_persistent_loading(self, part: IndexedVideoPart) -> None:
        self._persistent_thread = QThread(self)
        self._persistent_worker = PersistentVideoWorker(part)
        self._persistent_worker.moveToThread(self._persistent_thread)
        self._persistent_thread.started.connect(self._persistent_worker.run)
        self._persistent_worker.opened.connect(self._persistent_opened)
        self._persistent_worker.frame_ready.connect(self._persistent_frame_ready)
        self._persistent_worker.buffer_changed.connect(self._persistent_buffer_changed)
        self._persistent_worker.failed.connect(self._first_frame_failed)
        self._persistent_worker.finished.connect(self._persistent_thread.quit)
        self._persistent_worker.finished.connect(self._persistent_worker.deleteLater)
        self._persistent_thread.finished.connect(
            lambda thread=self._persistent_thread: self._persistent_finished(thread)
        )
        self._persistent_thread.start()

    @Slot(object)
    def _frame_sequence_ready(self, frames: list[DecodedFrame]) -> None:
        if not frames:
            self._first_frame_failed("La vidéo ne contient aucune image.")
            return
        if self._current_part_index < 0 or self._current_part_index >= len(self._video_parts):
            return
        part = self._video_parts[self._current_part_index]
        self._decoded_frames = frames
        self._current_frame_index = -1
        self._playback.load_sequence(
            frame_count=len(frames),
            fps=part.recording_fps,
            initial_index=0,
        )
        self.reader_widget.play_pause_button.setEnabled(len(frames) > 1)
        if self._pending_auto_play:
            self._pending_auto_play = False
            self._playback.play()

    def _show_previous_frame(self) -> None:
        if not self._playback.is_playing:
            self._playback.set_current_index(self._current_frame_index - 1)

    def _show_next_frame(self) -> None:
        if not self._playback.is_playing:
            self._playback.set_current_index(self._current_frame_index + 1)

    @Slot(int)
    def _playback_frame_changed(self, index: int) -> None:
        self._current_frame_index = index
        self._display_current_frame()

    def _display_current_frame(self) -> None:
        if self._current_frame_index < 0:
            return

        if self._persistent_mode:
            worker = self._persistent_worker
            if worker is None or self._persistent_waiting_for_frame:
                return

            cached = worker.buffer.get(self._current_frame_index)
            if cached is not None:
                self._show_decoded_frame(cached)
                worker.set_displayed_index(self._current_frame_index)
                return

            self._persistent_waiting_for_frame = True
            self._persistent_resume_after_frame = self._playback.is_playing
            if self._persistent_resume_after_frame:
                self._playback.pause()

            indices = worker.buffer.indices()

            print(
                f"[UI] Image demandée : {self._current_frame_index} | "
                f"Lecture : {self._playback.is_playing} | "
                f"En attente : {self._persistent_waiting_for_frame} | "
                f"Image présente : {worker.buffer.contains(self._current_frame_index)} | "
                f"Buffer : {indices}"
            )
            worker.request_frame(self._current_frame_index)
            return

        if self._current_frame_index >= len(self._decoded_frames):
            return
        self._show_decoded_frame(self._decoded_frames[self._current_frame_index])

    def _show_decoded_frame(self, frame: DecodedFrame) -> None:
        if self._current_part_index < 0 or self._current_part_index >= len(self._video_parts):
            return
        part = self._video_parts[self._current_part_index]
        frame_count = self._frame_count()
        timestamp = frame.absolute_timestamp.isoformat(timespec="milliseconds")
        self.reader_widget.video_widget.set_image(frame.image)
        self.reader_widget.frame_label.setText(f"Image : {frame.frame_number + 1}/{frame_count}")
        self.reader_widget.timestamp_label.setText(f"Horodatage : {timestamp}")
        self.reader_widget.set_frame_navigation_enabled(
            has_previous_frame=(not self._playback.is_playing and frame.frame_number > 0),
            has_next_frame=(not self._playback.is_playing and frame.frame_number + 1 < frame_count),
        )
        self.statusBar().showMessage(
            f"{part.video_path.name} | image {frame.frame_number + 1}/{frame_count}"
        )

    @Slot(str)
    def _first_frame_failed(self, message: str) -> None:
        self._playback.pause()
        self.reader_widget.video_widget.clear()
        self.reader_widget.frame_label.setText("Image : erreur")
        self.reader_widget.timestamp_label.setText("Horodatage : -")
        self._decoded_frames = []
        self._current_frame_index = -1
        self._persistent_waiting_for_frame = False
        self._persistent_resume_after_frame = False
        self.reader_widget.set_frame_navigation_enabled(False, False)
        self.reader_widget.play_pause_button.setEnabled(False)
        QMessageBox.critical(self, "Erreur vidéo", message)
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
            has_next_file=self._current_part_index + 1 < len(self._video_parts),
        )

    @Slot(bool)
    def _playback_state_changed(self, playing: bool) -> None:
        self.reader_widget.play_pause_button.setText("Pause" if playing else "Lecture")
        frame_count = self._frame_count()
        self.reader_widget.set_frame_navigation_enabled(
            has_previous_frame=(not playing and self._current_frame_index > 0),
            has_next_frame=(not playing and self._current_frame_index + 1 < frame_count),
        )
        if self._persistent_worker is not None:
            self._persistent_worker.set_playing(playing)

    @Slot(float)
    def _playback_speed_changed(self, speed: float) -> None:
        self.reader_widget.speed_control.set_speed(speed)
        if self._persistent_worker is not None:
            self._persistent_worker.set_playback_speed(speed)

    @Slot()
    def _playback_sequence_finished(self) -> None:
        next_index = self._current_part_index + 1
        if next_index >= len(self._video_parts):
            self._pending_auto_play = False
            self.statusBar().showMessage("Fin de la journée")
            return
        self._pending_auto_play = True
        self._open_part(next_index)

    @Slot(int, float)
    def _persistent_opened(self, frame_count: int, fps: float) -> None:
        self.statusBar().showMessage(
            f"Flux vidéo ouvert : {frame_count} images à {fps:.2f} FPS. Décodage..."
        )

        self._playback.load_sequence(
            frame_count=frame_count,
            fps=fps,
        )
        self.reader_widget.play_pause_button.setEnabled(False)

        if self._persistent_worker is not None:
            self._persistent_worker.set_playback_speed(self._playback.speed)
            self._persistent_worker.set_playing(False)
            self._persistent_worker.request_frame(0)

    @Slot(int, object)
    def _persistent_frame_ready(
        self,
        frame_index: int,
        frame: DecodedFrame,
    ) -> None:
        print(
            f"[UI] frame_ready reçu : {frame_index} | "
            f"Image attendue : {self._current_frame_index} | "
            f"En attente : {self._persistent_waiting_for_frame}"
        )
        if not self._persistent_mode or frame_index != self._current_frame_index:
            return
        self.statusBar().showMessage(f"Première image reçue : {frame_index}")
        resume_playback = self._persistent_resume_after_frame
        self._persistent_waiting_for_frame = False
        self._persistent_resume_after_frame = False
        self._show_decoded_frame(frame)

        if self._persistent_worker is not None:
            self._persistent_worker.set_displayed_index(frame_index)

        self.reader_widget.play_pause_button.setEnabled(
            self._persistent_buffer_ready and self._frame_count() > 1
        )
        if resume_playback or self._pending_auto_play:
            self._pending_auto_play = False
            self._playback.play()

    @Slot(int, int, int)
    def _persistent_buffer_changed(
        self,
        first_index: int,
        last_index: int,
        _used_bytes: int,
    ) -> None:
        if self._persistent_buffer_ready or self._current_part_index < 0:
            return

        # On attend seulement les 5 premières images.
        buffered_count = last_index - first_index + 1
        required_frames = min(5, self._frame_count())

        # Le tampon doit contenir le début de la vidéo.
        if first_index != 0 or buffered_count < required_frames:
            return

        self._persistent_buffer_ready = True
        self.reader_widget.play_pause_button.setEnabled(self._frame_count() > 1)
        self.statusBar().showMessage(f"Tampon vidéo prêt : {buffered_count} images")

    @Slot()
    def _persistent_finished(self, finished_thread=None) -> None:
        if finished_thread is None:
            return

        # Ne nettoyer les références actives que si c'est bien
        # le thread actuellement utilisé.
        if finished_thread is self._persistent_thread:
            self._persistent_worker = None
            self._persistent_thread = None
            self._persistent_mode = False
            self._update_file_navigation()

        # Supprimer uniquement le thread qui vient de se terminer.
        finished_thread.deleteLater()

    def _frame_count(self) -> int:
        if self._persistent_mode and 0 <= self._current_part_index < len(self._video_parts):
            return self._video_parts[self._current_part_index].frame_count
        return len(self._decoded_frames)

    def _stop_persistent_worker(self) -> bool:
        worker = self._persistent_worker
        thread = self._persistent_thread

        if worker is None and thread is None:
            self._persistent_mode = False
            return True

        if worker is not None:
            worker.stop()

        if thread is not None and not thread.wait(5000):
            print("[MainWindow] Le worker ne s'est pas arrêté après 5 s")

            thread.requestInterruption()
            thread.quit()

            if not thread.wait(2000):
                print("[MainWindow] ERREUR : le worker tourne toujours !")
                return False

        # Ne nettoyer que les références correspondant à ce thread.
        if self._persistent_thread is thread:
            self._persistent_worker = None
            self._persistent_thread = None

        self._persistent_mode = False
        return True

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
        self._playback.pause()
        if self._indexing_worker is not None:
            self._indexing_worker.cancel()
        if self._indexing_thread is not None:
            self._indexing_thread.quit()
            self._indexing_thread.wait(3000)
        self._stop_persistent_worker()
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
