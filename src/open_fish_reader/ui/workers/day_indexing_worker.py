from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ...services.day_indexing_service import (
    DayIndexingService,
    IndexingCancelledError,
)


class DayIndexingWorker(QObject):
    progress = Signal(int, int, str)
    completed = Signal(int, int, int)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(
        self,
        database_path: Path,
        station_folder: Path,
        day_folder: Path,
    ) -> None:
        super().__init__()
        self.database_path = database_path
        self.station_folder = station_folder
        self.day_folder = day_folder
        self._cancel_requested = False

    @Slot()
    def run(self) -> None:
        try:
            result = DayIndexingService().index_day(
                database_path=self.database_path,
                station_folder=self.station_folder,
                day_folder=self.day_folder,
                progress_callback=self.progress.emit,
                is_cancelled=lambda: self._cancel_requested,
            )
            self.completed.emit(*result)
        except IndexingCancelledError:
            self.cancelled.emit()
        except (OSError, ValueError, RuntimeError) as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        self._cancel_requested = True
