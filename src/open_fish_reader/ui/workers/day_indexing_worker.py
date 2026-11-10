from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ...services.day_indexing_service import DayIndexingService, IndexingCancelledError


class DayIndexingWorker(QObject):
    progress = Signal(int, int, str)
    completed = Signal(int, int, int, bool)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(
        self,
        database_path: Path,
        station_folder: Path,
        day_folder: Path,
        force: bool = False,
    ) -> None:
        super().__init__()
        self.database_path = database_path
        self.station_folder = station_folder
        self.day_folder = day_folder
        self.force = force
        self._cancel_requested = False

    @Slot()
    def run(self) -> None:
        try:
            result = DayIndexingService().index_day(
                self.database_path,
                self.station_folder,
                self.day_folder,
                self.progress.emit,
                lambda: self._cancel_requested,
                self.force,
            )
            self.completed.emit(
                result.event_count, result.part_count, result.duration_ms, result.skipped
            )
        except IndexingCancelledError:
            self.cancelled.emit()
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        self._cancel_requested = True
