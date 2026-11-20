from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QSettings,
    Qt,
    QThread,
    Slot,
)
from PySide6.QtGui import (
    QCloseEvent,
    QIcon,
    QKeyEvent,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QToolBar,
    QToolButton,
)

from ..core.exceptions import OpenFishReaderError
from ..core.paths import get_app_paths
from ..core.resources import resource_path
from ..core.system_open import open_folder
from ..database.connection import open_database
from ..database.repositories.size_calibration_repository import (
    SizeCalibrationRepository,
)
from ..domain.indexed_video_part import IndexedVideoPart
from ..services.database_backup_service import (
    DatabaseBackupService,
)
from ..services.database_information_service import (
    DatabaseInformationService,
)
from ..services.media_export_service import (
    MediaExportService,
)
from ..services.passage_service import (
    PassageInput,
    PassageService,
)
from ..services.playback_queue_service import PlaybackQueueService
from ..services.quick_observation_taxon_service import (
    QuickObservationTaxonService,
)
from ..services.station_service import OpenedStation, StationService
from ..services.video_part_status_service import VideoPartStatusService
from ..version import APP_NAME, APP_VERSION
from ..video.cache_policy import decide_full_cache
from ..video.frame import DecodedFrame
from ..video.playback_controller import PlaybackController
from .dialogs.about_dialog import AboutDialog
from .dialogs.day_selection_dialog import DaySelectionDialog
from .dialogs.indexing_progress_dialog import IndexingProgressDialog
from .dialogs.keyboard_shortcuts_dialog import (
    KeyboardShortcutsDialog,
)
from .dialogs.media_export_dialog import (
    MediaExportDialog,
)
from .dialogs.passage_list_dialog import (
    PassageListDialog,
)
from .dialogs.size_calibration_dialog import (
    SizeCalibrationDialog,
)
from .dialogs.taxon_configuration_dialog import TaxonConfigurationDialog
from .dialogs.user_guide_dialog import (
    UserGuideDialog,
)
from .widgets.quick_observation_panel import (
    ObservationDraft,
    QuickObservationPanel,
)
from .widgets.reader_widget import ReaderWidget
from .widgets.video_part_panel import VideoPartPanel
from .workers.day_indexing_worker import DayIndexingWorker
from .workers.frame_sequence_worker import FrameSequenceWorker
from .workers.persistent_video_worker import PersistentVideoWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowIcon(QIcon(str(resource_path("icons/open_fish_reader.ico"))))
        self._opened_station: OpenedStation | None = None
        self._station_service = StationService()
        self._passage_service = PassageService()
        self._playback_queue_service = PlaybackQueueService()
        self._decoded_frames: list[DecodedFrame] = []
        self._current_frame_index = -1

        self._database_backup_service = DatabaseBackupService()

        self._database_information_service = DatabaseInformationService()

        self._settings = QSettings()

        self._indexing_thread: QThread | None = None
        self._indexing_worker: DayIndexingWorker | None = None
        self._progress_dialog: IndexingProgressDialog | None = None
        self._frame_thread: QThread | None = None
        self._frame_worker: FrameSequenceWorker | None = None

        self._persistent_thread: QThread | None = None
        self._persistent_worker: PersistentVideoWorker | None = None
        self._persistent_mode = False
        self._persistent_buffer_ready = False
        self._persistent_total_frames = 0
        self._persistent_waiting_for_frame = False
        self._persistent_resume_after_frame = False
        self._displayed_frame: DecodedFrame | None = None

        self._current_day_folder: Path | None = None
        self._video_parts: list[IndexedVideoPart] = []
        self._current_part_index = -1
        self._pending_auto_play = False

        self.setWindowTitle(f"{APP_NAME} - {APP_VERSION}")
        self.resize(1200, 800)

        self.reader_widget = ReaderWidget()
        self.video_part_panel = VideoPartPanel()
        self.video_part_panel.open_requested.connect(self._open_part_from_panel)

        self.quick_observation_taxon_service = QuickObservationTaxonService()
        self.quick_observation_panel = QuickObservationPanel()
        self.quick_observation_panel.draft_requested.connect(self._create_passage_from_draft)

        self._passage_upstream_shortcut = QShortcut(
            QKeySequence("+"),
            self,
        )
        self._passage_unknown_shortcut = QShortcut(
            QKeySequence("0"),
            self,
        )
        self._passage_downstream_shortcut = QShortcut(
            QKeySequence("-"),
            self,
        )

        self._passage_upstream_shortcut.activated.connect(
            lambda: self._request_passage_direction(1)
        )
        self._passage_unknown_shortcut.activated.connect(lambda: self._request_passage_direction(0))
        self._passage_downstream_shortcut.activated.connect(
            lambda: self._request_passage_direction(-1)
        )

        self.reader_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.reader_splitter.setChildrenCollapsible(False)
        self.reader_splitter.addWidget(self.video_part_panel)
        self.reader_splitter.addWidget(self.reader_widget)
        self.reader_splitter.addWidget(self.quick_observation_panel)
        self.reader_splitter.setStretchFactor(0, 0)
        self.reader_splitter.setStretchFactor(1, 1)
        self.reader_splitter.setStretchFactor(2, 0)
        self.reader_splitter.setSizes([250, 850, 310])
        self.setCentralWidget(self.reader_splitter)
        self._playback = PlaybackController(self)
        self._playback.frame_changed.connect(self._playback_frame_changed)
        self._playback.playing_changed.connect(self._playback_state_changed)
        self._playback.speed_changed.connect(self._playback_speed_changed)
        self._playback.sequence_finished.connect(self._playback_sequence_finished)
        self._passage_dialog: PassageListDialog | None = None

        self.reader_widget.play_pause_button.clicked.connect(self._playback.toggle)
        self.reader_widget.speed_control.decrease_requested.connect(self._playback.decrease_speed)
        self.reader_widget.speed_control.increase_requested.connect(self._playback.increase_speed)
        self.reader_widget.speed_control.reset_requested.connect(self._playback.reset_speed)
        self.reader_widget.previous_file_button.clicked.connect(self._open_previous_file)
        self.reader_widget.next_file_button.clicked.connect(self._open_next_file)
        self.reader_widget.previous_frame_button.clicked.connect(self._show_previous_frame)
        self.reader_widget.next_frame_button.clicked.connect(self._show_next_frame)
        self.reader_widget.export_button.clicked.connect(self._open_media_export)
        self._video_part_status_service = VideoPartStatusService()
        self._requested_initial_frame = 0

        self._measurement_was_playing = False
        self.quick_observation_panel.measurement_requested.connect(self._start_measurement)

        self.reader_widget.video_widget.measurement_finished.connect(self._finish_measurement)

        self.reader_widget.video_widget.measurement_cancelled.connect(self._measurement_cancelled)
        self._media_export_service = MediaExportService()

        toolbar = QToolBar("Principal", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addAction("Ouvrir une station", self.open_station)
        self.day_action = toolbar.addAction("Choisir une journée", self.choose_day)
        self.day_action.setEnabled(False)
        toolbar.addSeparator()

        toolbar.addAction(
            "Passages",
            self._open_passage_list,
        )

        configuration_button = QToolButton(self)
        configuration_button.setText("Configuration")
        configuration_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        configuration_menu = QMenu(configuration_button)

        configuration_menu.addAction(
            "Liste des taxons…",
            self._open_taxon_configuration,
        )

        self._size_calibration_action = configuration_menu.addAction(
            "Relations taille / pixels…",
            self._open_size_calibrations,
        )

        configuration_button.setMenu(configuration_menu)

        toolbar.addWidget(configuration_button)

        toolbar.addSeparator()

        toolbar.addAction(
            "Sauvegarder la base…",
            self._backup_database,
        )

        toolbar.addSeparator()

        help_button = QToolButton(self)
        help_button.setText("Aide")
        help_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        help_menu = QMenu(help_button)
        help_menu.addAction(
            "Guide rapide…",
            self._show_user_guide,
        )

        help_menu.addAction(
            "Raccourcis clavier…",
            self._show_keyboard_shortcuts,
        )

        help_menu.addSeparator()

        help_menu.addAction(
            "Ouvrir le dossier des journaux",
            self._open_log_folder,
        )

        help_menu.addSeparator()

        help_menu.addAction(
            "À propos…",
            self._show_about,
        )
        help_button.setMenu(help_menu)
        toolbar.addWidget(help_button)
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

        logger.info(
            "Ouverture de station demandée : %s",
            selected_folder,
        )

        try:
            opened_station = self._station_service.open_station(Path(selected_folder))
        except (OpenFishReaderError, OSError, ValueError) as error:
            logger.exception(
                "Échec de l'ouverture de la station : %s",
                selected_folder,
            )
            QMessageBox.critical(self, "Station invalide", str(error))
            return

        self._playback.pause()
        self._stop_persistent_worker()
        self._stop_frame_worker()
        self._displayed_frame = None
        self._close_opened_station()
        self._opened_station = opened_station
        logger.info(
            ("Station ouverte : %s | base=%s | jours=%s"),
            opened_station.station.name,
            opened_station.database_path,
            opened_station.detected_day_count,
        )
        self._reload_quick_observation_taxa()
        self._video_parts = []
        self._current_part_index = -1
        self._current_day_folder = None
        self.reader_widget.export_button.setEnabled(False)
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
        self.video_part_panel.set_parts(self._video_parts)
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

        if not self._video_parts:
            self.reader_widget.clear_video_information()
            self.video_part_panel.set_parts([])
            self.reader_widget.set_navigation_enabled(
                False,
                False,
            )

            QMessageBox.information(
                self,
                "Journée vide",
                "Aucune partie vidéo valide n'est disponible pour cette journée.",
            )
            return

        self._open_part(0)

    @Slot(str)
    def _indexing_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Erreur d'indexation", message)
        self.statusBar().showMessage("Échec de l'indexation")
        logger.error(
            "Échec de l'indexation : %s",
            message,
        )

    @Slot()
    def _indexing_cancelled(self) -> None:
        self.statusBar().showMessage("Indexation annulée")
        logger.info("Indexation annulée")

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
        if self.reader_widget.video_widget.measurement_active:
            return

        self._pending_auto_play = self._playback.is_playing
        self._requested_initial_frame = 0

        self._open_part(self._current_part_index - 1)

    def _open_next_file(self) -> None:
        if self._current_part_index + 1 >= len(self._video_parts):
            return
        if self.reader_widget.video_widget.measurement_active:
            return

        self._pending_auto_play = self._playback.is_playing
        self._requested_initial_frame = 0

        self._open_part(self._current_part_index + 1)

    def _open_part(self, index: int) -> None:
        if self._frame_thread is not None:
            return
        if index < 0 or index >= len(self._video_parts):
            self.reader_widget.export_button.setEnabled(False)
            return
        if self.reader_widget.video_widget.measurement_active:
            return

        self.reader_widget.export_button.setEnabled(False)

        # Sauvegarde de l'ancien fichier avant de
        # changer _current_part_index.
        self._save_current_video_position()

        self._playback.pause()

        if not self._stop_persistent_worker():
            QMessageBox.warning(
                self,
                "Lecteur vidéo occupé",
                "Le fichier vidéo précédent ne peut pas encore être fermé.",
            )
            return
        self._current_part_index = index
        self.video_part_panel.set_current_row(index)
        self.video_part_panel.mark_in_progress(index)
        part = self._video_parts[index]
        if self._opened_station is not None:
            self._video_part_status_service.mark_opened(
                self._opened_station.database_path,
                part.id,
            )
        self.reader_widget.export_button.setEnabled(part.video_path.is_file())

        self._decoded_frames = []
        self._current_frame_index = -1
        self._persistent_mode = False
        self._persistent_buffer_ready = False
        self._persistent_total_frames = 0
        self._persistent_waiting_for_frame = False
        self._persistent_resume_after_frame = False
        self._persistent_requested_frame_index = None
        self._displayed_frame = None

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
            self._start_full_cache_loading(part)
            return

        self._persistent_mode = True
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
        self._persistent_worker.stream_ended.connect(self._persistent_stream_ended)
        self._persistent_worker.failed.connect(self._first_frame_failed)
        self._persistent_worker.finished.connect(
            self._persistent_thread.quit,
            Qt.ConnectionType.DirectConnection,
        )

        self._persistent_thread.finished.connect(self._persistent_worker.deleteLater)

        self._persistent_thread.finished.connect(self._persistent_finished)
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

        initial_index = min(
            self._requested_initial_frame,
            len(frames) - 1,
        )

        self._playback.load_sequence(
            frame_count=len(frames),
            fps=part.recording_fps,
            initial_index=initial_index,
        )

        self._requested_initial_frame = 0
        self.reader_widget.play_pause_button.setEnabled(len(frames) > 1)
        if self._pending_auto_play:
            self._pending_auto_play = False
            self._playback.play()

    def _show_previous_frame(self) -> None:
        if self._playback.is_playing or self._persistent_waiting_for_frame:
            return

        self._playback.set_current_index(self._current_frame_index - 1)

    def _show_next_frame(self) -> None:
        if self._playback.is_playing or self._persistent_waiting_for_frame:
            return

        self._playback.set_current_index(self._current_frame_index + 1)

    @Slot(int)
    def _playback_frame_changed(self, index: int) -> None:
        self._current_frame_index = index
        self._display_current_frame()

    def _display_current_frame(self) -> None:
        if self._current_frame_index < 0:
            return

        if not self._persistent_mode:
            if self._current_frame_index >= len(self._decoded_frames):
                return

            frame = self._decoded_frames[self._current_frame_index]
            self._show_decoded_frame(frame)
            return

        worker = self._persistent_worker

        if worker is None:
            return

        # Une seule demande distante peut être active.
        if self._persistent_waiting_for_frame:
            return

        cached_frame = worker.buffer.get(self._current_frame_index)

        if cached_frame is not None:
            self._show_decoded_frame(cached_frame)
            worker.set_displayed_index(self._current_frame_index)
            return

        requested_index = self._current_frame_index

        self._persistent_waiting_for_frame = True
        self._persistent_requested_frame_index = requested_index
        self._persistent_resume_after_frame = self._playback.is_playing

        # Empêcher un second déplacement logique pendant
        # le seek.
        self.reader_widget.set_frame_navigation_enabled(
            False,
            False,
        )
        self.reader_widget.play_pause_button.setEnabled(False)

        if self._playback.is_playing:
            self._playback.pause()

        worker.request_frame(requested_index)

    def _show_decoded_frame(self, frame: DecodedFrame) -> None:
        if self._current_part_index < 0 or self._current_part_index >= len(self._video_parts):
            return
        self._displayed_frame = frame
        frame_count = self._frame_count()
        timestamp = frame.absolute_timestamp.isoformat(timespec="milliseconds")
        self.reader_widget.video_widget.set_image(frame.image)
        self.reader_widget.frame_label.setText(f"Image : {frame.frame_number + 1}/{frame_count}")
        self.reader_widget.timestamp_label.setText(f"Horodatage : {timestamp}")
        self.reader_widget.set_frame_navigation_enabled(
            has_previous_frame=(not self._playback.is_playing and frame.frame_number > 0),
            has_next_frame=(not self._playback.is_playing and frame.frame_number + 1 < frame_count),
        )

    @Slot(str)
    def _first_frame_failed(
        self,
        message: str,
    ) -> None:
        self._playback.pause()

        failed_part_index = self._current_part_index
        video_part_id = self._current_video_part_id()

        self._persistent_waiting_for_frame = False
        self._persistent_requested_frame_index = None
        self._persistent_resume_after_frame = False
        self._displayed_frame = None

        self.reader_widget.video_widget.clear()
        self.reader_widget.frame_label.setText("Image : erreur")
        self.reader_widget.timestamp_label.setText("Horodatage : -")
        self.reader_widget.set_frame_navigation_enabled(
            False,
            False,
        )
        self.reader_widget.play_pause_button.setEnabled(False)

        if self._opened_station is not None and video_part_id is not None:
            self._video_part_status_service.mark_error(
                self._opened_station.database_path,
                video_part_id,
                message,
            )

        if failed_part_index >= 0:
            self.video_part_panel.mark_error(
                failed_part_index,
                message,
            )

        self._decoded_frames = []
        self._current_frame_index = -1

        QMessageBox.critical(
            self,
            "Erreur vidéo",
            message,
        )
        self.statusBar().showMessage("Échec du décodage vidéo")
        logger.error(
            "Échec du décodage vidéo : %s",
            message,
        )

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

    @Slot(int, float)
    def _persistent_opened(self, frame_count: int, fps: float) -> None:
        self._persistent_total_frames = frame_count
        initial_index = min(
            self._requested_initial_frame,
            frame_count - 1,
        )

        self._playback.load_sequence(
            frame_count=frame_count,
            fps=fps,
            initial_index=initial_index,
        )
        self.reader_widget.play_pause_button.setEnabled(False)
        if self._persistent_worker is not None:
            self._persistent_worker.set_playback_speed(self._playback.speed)
            self._persistent_worker.set_playing(False)
            self._persistent_worker.request_frame(initial_index)
        self._requested_initial_frame = 0

    @Slot(int, object)
    def _persistent_frame_ready(
        self,
        frame_index: int,
        frame: DecodedFrame,
    ) -> None:
        if not self._persistent_mode:
            return

        requested_index = self._persistent_requested_frame_index

        # Une réponse obsolète ne doit pas libérer une
        # autre demande, mais une réponse attendue doit
        # toujours déverrouiller l'interface.
        if requested_index is not None and frame_index != requested_index:
            return

        resume_playback = self._persistent_resume_after_frame

        self._persistent_waiting_for_frame = False
        self._persistent_requested_frame_index = None
        self._persistent_resume_after_frame = False

        # La position logique devient celle réellement
        # reçue après le seek.
        self._current_frame_index = frame_index
        self._playback.set_current_index(frame_index)

        self._show_decoded_frame(frame)

        worker = self._persistent_worker

        if worker is not None:
            worker.set_displayed_index(frame_index)

        self.reader_widget.play_pause_button.setEnabled(
            self._persistent_buffer_ready and self._frame_count() > 1
        )

        self.reader_widget.set_frame_navigation_enabled(
            has_previous_frame=(frame_index > 0),
            has_next_frame=(frame_index + 1 < self._frame_count()),
        )

        if resume_playback:
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

        buffered_count = last_index - first_index + 1
        part = self._video_parts[self._current_part_index]

        if self._pending_auto_play:
            required_seconds = 0.75
        else:
            required_seconds = 1.5

        required_frames = min(
            self._frame_count(),
            max(5, round(part.recording_fps * required_seconds)),
        )
        if first_index != 0 or buffered_count < required_frames:
            return

        self._persistent_buffer_ready = True
        self.reader_widget.play_pause_button.setEnabled(self._frame_count() > 1)

        # Un changement automatique de fichier attend un vrai tampon, pas
        # seulement la première image, afin de conserver la fluidité.
        if self._pending_auto_play:
            self._pending_auto_play = False
            self._playback.play()

    @Slot(int)
    def _persistent_stream_ended(
        self,
        actual_frame_count: int,
    ) -> None:
        if not self._persistent_mode or actual_frame_count <= 0:
            return

        self._persistent_total_frames = actual_frame_count

        self._playback.set_frame_count(actual_frame_count)
        self._persistent_waiting_for_frame = False
        self._persistent_resume_after_frame = False

    @Slot()
    def _persistent_finished(self) -> None:
        self._update_file_navigation()

    def _frame_count(self) -> int:
        if self._persistent_mode:
            return self._persistent_total_frames
        return len(self._decoded_frames)

    def _stop_persistent_worker(self) -> bool:
        worker = self._persistent_worker
        thread = self._persistent_thread

        if worker is None and thread is None:
            self._persistent_mode = False
            return True

        self._playback.pause()

        if worker is not None:
            # stop() ne réalise aucun décodage.
            # Il positionne un threading.Event thread-safe.
            worker.stop()

        if thread is not None:
            # Enregistre également une demande de sortie
            # de la boucle événementielle du QThread.
            thread.requestInterruption()
            thread.quit()

            if not thread.wait(5000):
                self.statusBar().showMessage("Le décodeur vidéo ne s'est pas arrêté.")
                return False

            thread.deleteLater()

        if self._persistent_worker is worker:
            self._persistent_worker = None

        if self._persistent_thread is thread:
            self._persistent_thread = None

        self._persistent_mode = False
        self._persistent_buffer_ready = False
        self._persistent_waiting_for_frame = False
        self._persistent_resume_after_frame = False
        self._persistent_requested_frame_index = None

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
        logger.info("Fermeture de la fenêtre principale")
        self._playback.pause()
        self._save_current_video_position()
        if self._indexing_worker is not None:
            self._indexing_worker.cancel()
        if self._indexing_thread is not None:
            self._indexing_thread.quit()
            self._indexing_thread.wait(3000)
        self._stop_persistent_worker()
        self._stop_frame_worker()
        self._close_opened_station()
        super().closeEvent(event)

    def keyPressEvent(
        self,
        event: QKeyEvent,
    ) -> None:
        modifiers = event.modifiers()
        key = event.key()

        if self.reader_widget.video_widget.measurement_active:
            return

        # Les raccourcis de vitesse restent utilisables
        # même si le focus est dans un champ du panneau.
        if modifiers & Qt.KeyboardModifier.ControlModifier and key in (
            Qt.Key.Key_Plus,
            Qt.Key.Key_Equal,
        ):
            self._playback.increase_speed()
            event.accept()
            return

        if modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Minus:
            self._playback.decrease_speed()
            event.accept()
            return

        focused_widget = self.focusWidget()

        editing_field = isinstance(
            focused_widget,
            (
                QLineEdit,
                QTextEdit,
                QSpinBox,
                QComboBox,
            ),
        )

        # Dans un champ de saisie, Qt conserve les
        # lettres, chiffres, signes, flèches et espace.
        if editing_field:
            super().keyPressEvent(event)
            return

        # Navigation vidéo uniquement sans Ctrl,
        # Maj ou Alt.
        if modifiers == Qt.KeyboardModifier.NoModifier:
            if key == Qt.Key.Key_Left:
                self._show_previous_frame()
                event.accept()
                return

            if key == Qt.Key.Key_Right:
                self._show_next_frame()
                event.accept()
                return

            if key == Qt.Key.Key_Up:
                self._open_previous_file()
                event.accept()
                return

            if key == Qt.Key.Key_Down:
                self._open_next_file()
                event.accept()
                return

            if key == Qt.Key.Key_Space:
                if not self._persistent_waiting_for_frame:
                    self._playback.toggle()

                event.accept()
                return

            # Sélection du taxon par son raccourci.
            text = event.text().strip().upper()

            if text and self.quick_observation_panel.select_taxon_by_shortcut(text):
                event.accept()
                return

        super().keyPressEvent(event)

    @Slot()
    def _playback_sequence_finished(
        self,
    ) -> None:
        current_part_index = self._current_part_index
        video_part_id = self._current_video_part_id()

        if self._opened_station is not None and video_part_id is not None:
            self._video_part_status_service.mark_completed(
                self._opened_station.database_path,
                video_part_id,
                self._current_frame_index,
            )

        if current_part_index >= 0:
            self.video_part_panel.mark_read(current_part_index)

        next_index = current_part_index + 1

        if next_index >= len(self._video_parts):
            self._pending_auto_play = False

            self.reader_widget.play_pause_button.setText("Lecture")
            self.reader_widget.play_pause_button.setEnabled(False)
            self.reader_widget.set_frame_navigation_enabled(
                has_previous_frame=(self._current_frame_index > 0),
                has_next_frame=False,
            )
            self.statusBar().showMessage("Fin de la journée")
            return

        self._pending_auto_play = True
        self._open_part(next_index)

    def _open_part_from_panel(
        self,
        index: int,
    ) -> None:
        if not (0 <= index < len(self._video_parts)):
            return

        part = self._video_parts[index]

        self._pending_auto_play = False
        self._requested_initial_frame = (
            part.last_viewed_frame if part.last_viewed_frame is not None else 0
        )

        self._open_part(index)

    def _current_video_part_id(self) -> int | None:
        if not 0 <= self._current_part_index < len(self._video_parts):
            return None
        return self._video_parts[self._current_part_index].id

    def _save_current_video_position(
        self,
    ) -> None:
        if self._opened_station is None or self._current_frame_index < 0:
            return

        video_part_id = self._current_video_part_id()

        if video_part_id is None:
            return

        self._video_part_status_service.update_position(
            self._opened_station.database_path,
            video_part_id,
            self._current_frame_index,
        )

    def _open_taxon_configuration(self) -> None:
        if self._opened_station is None:
            QMessageBox.information(
                self,
                "Aucune station",
                "Ouvrez d'abord une station pour configurer son catalogue.",
            )
            return

        dialog = TaxonConfigurationDialog(
            self._opened_station.database_path,
            self,
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._reload_quick_observation_taxa()

    def _reload_quick_observation_taxa(self) -> None:
        if self._opened_station is None:
            self.quick_observation_panel.set_taxa([])
            return

        taxa = self.quick_observation_taxon_service.list_active(self._opened_station.database_path)
        self.quick_observation_panel.set_taxa(taxa)

    @Slot(object)
    def _preview_observation_draft(
        self,
        draft: ObservationDraft,
    ) -> None:
        direction_labels = {
            -1: "dévalaison",
            0: "indéterminé",
            1: "montaison",
        }
        self.statusBar().showMessage(
            f"Brouillon : {draft.tax_code} ×{draft.individual_count} — "
            f"{direction_labels[draft.direction]}. "
            "Aucune donnée n'a encore été enregistrée."
        )
        self.quick_observation_panel.reset_after_draft()

    @Slot(object)
    def _create_passage_from_draft(
        self,
        draft: ObservationDraft,
    ) -> None:
        if self._opened_station is None:
            QMessageBox.information(
                self,
                "Aucune station",
                "Ouvrez d'abord une station.",
            )
            return

        video_part_id = self._current_video_part_id()

        if video_part_id is None:
            QMessageBox.information(
                self,
                "Aucune séquence",
                "Ouvrez d'abord une séquence vidéo.",
            )
            return

        frame = self._displayed_frame

        if frame is None:
            QMessageBox.information(
                self,
                "Aucune image",
                "Aucune image vidéo n'est actuellement affichée.",
            )
            return

        was_playing = self._playback.is_playing

        if was_playing:
            self._playback.pause()

        try:
            self._passage_service.create(
                self._opened_station.database_path,
                PassageInput(
                    station_id=(self._opened_station.station_id),
                    video_part_id=video_part_id,
                    taxon_id=draft.taxon_id,
                    frame_number=(frame.frame_number),
                    position_ms=frame.position_ms,
                    observed_at=(frame.absolute_timestamp),
                    individual_count=(draft.individual_count),
                    direction=draft.direction,
                    confidence=draft.confidence,
                    needs_review=(draft.needs_review),
                    glass_position=(draft.glass_position),
                    length_mm=draft.length_mm,
                    length_pixels=draft.length_pixels,
                    calibration_id=draft.calibration_id,
                    measurement_method=(draft.measurement_method),
                    measurement_points=(draft.measurement_points),
                    comment=draft.comment,
                ),
            )

        except (
            OSError,
            RuntimeError,
            ValueError,
        ) as error:
            QMessageBox.critical(
                self,
                "Enregistrement impossible",
                str(error),
            )
            return

        logger.info(
            ("Passage créé : video_part_id=%s taxon_id=%s frame=%s count=%s direction=%s"),
            video_part_id,
            draft.taxon_id,
            frame.frame_number,
            draft.individual_count,
            draft.direction,
        )

        self._update_video_part_observation_count(video_part_id)

        if self._passage_dialog is not None and self._passage_dialog.isVisible():
            self._passage_dialog.reload()

        self.quick_observation_panel.reset_after_draft()

        direction_labels = {
            -1: "dévalaison",
            0: "sens indéterminé",
            1: "montaison",
        }

        self.statusBar().showMessage(
            f"Passage enregistré : "
            f"{draft.tax_code} "
            f"×{draft.individual_count}, "
            f"{direction_labels[draft.direction]}, "
            f"image {frame.frame_number + 1}"
        )

        if was_playing:
            self._playback.play()

    def _update_video_part_observation_count(
        self,
        video_part_id: int,
    ) -> None:
        if self._opened_station is None:
            return

        connection = open_database(self._opened_station.database_path)

        try:
            row = connection.execute(
                """
                SELECT
                    observation_count,
                    review_status
                FROM video_parts
                WHERE id = ?
                """,
                (video_part_id,),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            return

        observation_count = int(row["observation_count"])

        target_index = None

        for index, part in enumerate(self._video_parts):
            if part.id == video_part_id:
                target_index = index
                break

        if target_index is None:
            return

        self.video_part_panel.set_observation_count(
            target_index,
            observation_count,
        )

    def _request_passage_direction(
        self,
        direction: int,
    ) -> None:
        focused_widget = self.focusWidget()

        if isinstance(
            focused_widget,
            (
                QLineEdit,
                QTextEdit,
                QSpinBox,
                QComboBox,
            ),
        ):
            return

        if self._persistent_waiting_for_frame:
            return

        if (
            self._opened_station is None
            or self._current_part_index < 0
            or self._displayed_frame is None
        ):
            self.statusBar().showMessage("Aucune image disponible pour enregistrer un passage.")
            return

        if not (self.quick_observation_panel.request_direction(direction)):
            self.statusBar().showMessage("Sélectionnez d'abord une espèce.")

    def _open_passage_list(self) -> None:
        if self._opened_station is None:
            QMessageBox.information(
                self,
                "Aucune station",
                "Ouvrez d'abord une station.",
            )
            return

        current_day = None

        if self._current_day_folder is not None:
            try:
                current_day = datetime.strptime(
                    self._current_day_folder.name,
                    "%Y-%m-%d",
                ).date()
            except ValueError:
                current_day = None

        if self._passage_dialog is not None and self._passage_dialog.isVisible():
            self._passage_dialog.raise_()
            self._passage_dialog.activateWindow()
            self._passage_dialog.reload()
            return

        self._passage_dialog = PassageListDialog(
            database_path=(self._opened_station.database_path),
            station_id=(self._opened_station.station_id),
            current_day=current_day,
            parent=self,
        )

        self._passage_dialog.passage_open_requested.connect(self._open_passage_in_reader)
        self._passage_dialog.passages_changed.connect(self._update_video_part_observation_count)

        self._passage_dialog.finished.connect(self._passage_dialog_closed)

        self._passage_dialog.show()

    def _passage_dialog_closed(
        self,
        _result: int,
    ) -> None:
        if self._passage_dialog is not None:
            self._passage_dialog.deleteLater()

        self._passage_dialog = None

    @Slot(int, int)
    def _open_passage_in_reader(
        self,
        video_part_id: int,
        frame_number: int,
    ) -> None:
        target_index = None

        for index, part in enumerate(self._video_parts):
            if part.id == video_part_id:
                target_index = index
                break

        if target_index is None:
            QMessageBox.warning(
                self,
                "Séquence indisponible",
                ("La séquence du passage n'est pas chargée dans la journée courante."),
            )
            return

        self._pending_auto_play = False
        self._requested_initial_frame = max(
            0,
            frame_number,
        )

        self._open_part(target_index)

    def _open_size_calibrations(
        self,
    ) -> None:
        if self._opened_station is None:
            QMessageBox.information(
                self,
                "Aucune station",
                "Ouvrez d'abord une station.",
            )
            return

        dialog = SizeCalibrationDialog(
            database_path=(self._opened_station.database_path),
            station_id=(self._opened_station.station_id),
            parent=self,
        )

        dialog.exec()

    def _start_measurement(self) -> None:
        if self._opened_station is None or self._displayed_frame is None:
            QMessageBox.information(
                self,
                "Mesure impossible",
                "Aucune image n'est affichée.",
            )
            return

        self._measurement_was_playing = self._playback.is_playing
        self._playback.pause()

        if not (self.reader_widget.video_widget.start_measurement()):
            return

        self.statusBar().showMessage(
            "Mesure : cliquez le long du "
            "poisson. Entrée ou double-clic "
            "pour terminer, Ctrl+Z pour "
            "retirer un point, Échap pour "
            "annuler."
        )

    @Slot(object, float)
    def _finish_measurement(
        self,
        points: tuple[tuple[float, float], ...],
        length_pixels: float,
    ) -> None:
        if self._opened_station is None or self._displayed_frame is None:
            return

        connection = open_database(self._opened_station.database_path)

        try:
            calibration = SizeCalibrationRepository(connection).find_for_timestamp(
                self._opened_station.station_id,
                self._displayed_frame.absolute_timestamp,
            )
        finally:
            connection.close()

        if calibration is None:
            QMessageBox.warning(
                self,
                "Aucune calibration",
                "Aucune relation taille / pixels n'est valide à l'horodatage de cette image.",
            )
            return

        glass_position = str(self.quick_observation_panel.glass_position_combo.currentData())

        ratio = calibration.ratio_for_position(glass_position)

        length_mm = round(length_pixels * ratio)

        self.quick_observation_panel.set_polyline_measurement(
            points=points,
            length_pixels=length_pixels,
            length_mm=length_mm,
            calibration_id=calibration.id,
        )

        self.statusBar().showMessage(
            f"Mesure prête : {len(points)} points, {length_pixels:.1f} px, {length_mm} mm"
        )

    @Slot()
    def _measurement_cancelled(
        self,
    ) -> None:
        self.statusBar().showMessage("Mesure annulée.")

    def _open_media_export(self) -> None:
        if (
            self._opened_station is None
            or self._current_part_index < 0
            or self._current_part_index >= len(self._video_parts)
        ):
            return

        part = self._video_parts[self._current_part_index]
        frame = self._displayed_frame

        if self._playback.is_playing:
            self._playback.pause()

        taxa = self.quick_observation_taxon_service.list_active(self._opened_station.database_path)

        selected_taxon = self.quick_observation_panel.selected_taxon

        dialog = MediaExportDialog(
            taxa,
            image_available=frame is not None,
            video_available=(part.video_path.is_file()),
            selected_taxon_id=(selected_taxon.id if selected_taxon is not None else None),
            parent=self,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        request = dialog.request()

        try:
            result = self._media_export_service.export(
                request,
                image=(frame.image if frame is not None else None),
                source_video_path=(part.video_path),
                station_slug=(self._opened_station.station.slug),
                observed_at=(
                    frame.absolute_timestamp if frame is not None else datetime.now().astimezone()
                ),
                frame_number=(frame.frame_number if frame is not None else 0),
            )

        except (
            OSError,
            ValueError,
        ) as error:
            QMessageBox.critical(
                self,
                "Export impossible",
                str(error),
            )
            return

        exported_paths = [
            str(path)
            for path in (
                result.image_path,
                result.video_path,
            )
            if path is not None
        ]

        QMessageBox.information(
            self,
            "Export terminé",
            ("Fichier(s) exporté(s) :\n\n" + "\n".join(exported_paths)),
        )
        logger.info(
            "Export média terminé : %s",
            exported_paths,
        )

    def _open_log_folder(self) -> None:
        log_folder = get_app_paths().logs
        try:
            open_folder(log_folder)
        except Exception as error:
            logger.exception("Impossible d'ouvrir le dossier des journaux")
            QMessageBox.warning(
                self,
                "Dossier inaccessible",
                f"Impossible d'ouvrir le dossier :\n\n{log_folder}\n\n{error}",
            )

    def _backup_database(self) -> None:
        if self._opened_station is None:
            QMessageBox.information(
                self,
                "Aucune station",
                "Ouvrez d'abord une station.",
            )
            return

        initial_folder = self._settings.value(
            "database_backup/destination_folder",
            str(get_app_paths().backups),
            type=str,
        )

        destination = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier de sauvegarde",
            initial_folder,
        )

        if not destination:
            return

        try:
            result = self._database_backup_service.backup(
                self._opened_station.database_path,
                Path(destination),
                self._opened_station.station.slug,
            )

        except (
            OSError,
            RuntimeError,
            ValueError,
        ) as error:
            logger.exception("Échec de la sauvegarde de la base")

            QMessageBox.critical(
                self,
                "Sauvegarde impossible",
                str(error),
            )
            return

        self._settings.setValue(
            "database_backup/destination_folder",
            destination,
        )

        logger.info(
            "Base sauvegardée : %s",
            result.output_path,
        )

        QMessageBox.information(
            self,
            "Sauvegarde terminée",
            (f"Base sauvegardée et vérifiée :\n\n{result.output_path}"),
        )

    def _show_about(self) -> None:
        information = None

        if self._opened_station is not None:
            try:
                information = self._database_information_service.read(
                    self._opened_station.database_path
                )

            except (
                OSError,
                RuntimeError,
            ) as error:
                logger.exception("Lecture des informations de base impossible")

                QMessageBox.warning(
                    self,
                    "Informations incomplètes",
                    str(error),
                )

        dialog = AboutDialog(
            information,
            self,
        )
        dialog.exec()

    def _show_user_guide(self) -> None:
        UserGuideDialog(self).exec()

    def _show_keyboard_shortcuts(
        self,
    ) -> None:
        KeyboardShortcutsDialog(self).exec()
