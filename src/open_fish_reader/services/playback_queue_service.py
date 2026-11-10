from __future__ import annotations

from pathlib import Path

from ..database.connection import open_database
from ..database.repositories.video_part_repository import VideoPartRepository
from ..domain.indexed_video_part import IndexedVideoPart


class PlaybackQueueService:
    def load_day(
        self, database_path: Path, station_folder: Path, day_date: str
    ) -> list[IndexedVideoPart]:
        connection = open_database(database_path)
        try:
            return VideoPartRepository(connection).list_for_day(day_date, station_folder)
        finally:
            connection.close()
