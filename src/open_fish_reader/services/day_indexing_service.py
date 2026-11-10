from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ..core.exceptions import IgnoredJsonRecordError
from ..database.connection import open_database
from ..database.repositories.day_repository import DayRepository
from ..database.repositories.event_repository import EventRepository
from ..domain.video_part import VideoPart
from ..indexing.day_scanner import find_video_part_json_files
from ..indexing.event_builder import build_events
from ..indexing.json_parser import parse_video_part_json

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[int, int, str], None]
CancelCallback = Callable[[], bool]


class IndexingCancelledError(Exception):
    """L'indexation a été annulée par l'utilisateur."""


class DayIndexingService:
    def index_day(
        self,
        database_path: Path,
        station_folder: Path,
        day_folder: Path,
        progress_callback: ProgressCallback,
        is_cancelled: CancelCallback,
    ) -> tuple[int, int, int]:
        json_files = find_video_part_json_files(day_folder)
        total = len(json_files)
        video_parts: list[VideoPart] = []

        for position, json_path in enumerate(json_files, start=1):
            if is_cancelled():
                raise IndexingCancelledError

            progress_callback(position - 1, total, json_path.name)
            try:
                video_parts.append(parse_video_part_json(json_path))
            except IgnoredJsonRecordError as error:
                LOGGER.info("%s : %s", json_path, error)

        events = build_events(video_parts)
        progress_callback(total, total, "Enregistrement dans SQLite...")

        connection = open_database(database_path)
        now = datetime.now().astimezone()
        try:
            station_row = connection.execute("SELECT id FROM stations LIMIT 1").fetchone()
            if station_row is None:
                raise RuntimeError("La station n'existe pas dans la base SQLite.")

            station_id = int(station_row["id"])
            part_count = sum(len(event.parts) for event in events)
            duration_ms = round(
                sum(part.duration_seconds for event in events for part in event.parts) * 1000
            )
            first_time = (
                events[0].event_start_time.isoformat(timespec="milliseconds") if events else None
            )
            last_time = (
                events[-1].parts[-1].video_end_time.isoformat(timespec="milliseconds")
                if events
                else None
            )

            with connection:
                day_id = DayRepository(connection).upsert(
                    station_id=station_id,
                    day_date=datetime.strptime(day_folder.name, "%Y-%m-%d").date(),
                    relative_folder=day_folder.relative_to(station_folder),
                    event_count=len(events),
                    video_part_count=part_count,
                    total_video_duration_ms=duration_ms,
                    first_event_time=first_time,
                    last_event_time=last_time,
                    now=now,
                )
                EventRepository(connection).replace_day_events(
                    day_id=day_id,
                    station_folder=station_folder,
                    events=events,
                    now=now,
                )
        finally:
            connection.close()

        return len(events), part_count, duration_ms
