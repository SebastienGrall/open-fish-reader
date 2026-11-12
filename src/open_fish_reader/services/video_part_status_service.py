from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..database.connection import open_database
from ..database.repositories.video_part_status_repository import (
    VideoPartStatusRepository,
)


class VideoPartStatusService:
    def mark_opened(self, database_path: Path, video_part_id: int) -> None:
        self._execute(
            database_path, lambda repository, now: repository.mark_opened(video_part_id, now)
        )

    def update_position(
        self,
        database_path: Path,
        video_part_id: int,
        frame_index: int,
    ) -> None:
        self._execute(
            database_path,
            lambda repository, now: repository.update_position(
                video_part_id,
                frame_index,
                now,
            ),
        )

    def mark_completed(
        self,
        database_path: Path,
        video_part_id: int,
        final_frame_index: int,
    ) -> None:
        self._execute(
            database_path,
            lambda repository, now: repository.mark_completed(
                video_part_id,
                final_frame_index,
                now,
            ),
        )

    def mark_error(
        self,
        database_path: Path,
        video_part_id: int,
        message: str,
    ) -> None:
        self._execute(
            database_path,
            lambda repository, now: repository.mark_error(
                video_part_id,
                message,
                now,
            ),
        )

    @staticmethod
    def _execute(database_path: Path, operation) -> None:
        connection = open_database(database_path)
        try:
            now = datetime.now().astimezone()
            with connection:
                operation(VideoPartStatusRepository(connection), now)
        finally:
            connection.close()
