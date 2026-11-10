from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..core.exceptions import IgnoredJsonRecordError
from ..database.connection import open_database
from ..database.repositories.day_repository import DayRepository
from ..database.repositories.event_repository import EventRepository
from ..domain.video_part import VideoPart
from ..indexing.day_scanner import find_video_part_json_files
from ..indexing.day_signature import compute_day_signature
from ..indexing.event_builder import build_events
from ..indexing.json_parser import parse_video_part_json

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[int, int, str], None]
CancelCallback = Callable[[], bool]


class IndexingCancelledError(Exception):
    """L'indexation a été annulée par l'utilisateur."""


@dataclass(frozen=True, slots=True)
class DayIndexingResult:
    event_count: int
    part_count: int
    duration_ms: int
    skipped: bool


class DayIndexingService:
    def index_day(
        self,
        database_path: Path,
        station_folder: Path,
        day_folder: Path,
        progress_callback: ProgressCallback,
        is_cancelled: CancelCallback,
        force: bool = False,
    ) -> DayIndexingResult:
        signature, json_count = compute_day_signature(day_folder)
        connection = open_database(database_path)
        try:
            station_row = connection.execute("SELECT id FROM stations LIMIT 1").fetchone()
            if station_row is None:
                raise RuntimeError("La station n'existe pas dans SQLite.")
            station_id = int(station_row["id"])
            day_date = datetime.strptime(day_folder.name, "%Y-%m-%d").date()
            existing = DayRepository(connection).get_by_date(station_id, day_date)
            if (
                not force
                and existing is not None
                and existing["source_signature"] == signature
                and int(existing["source_json_count"]) == json_count
            ):
                progress_callback(json_count, json_count, "Journée inchangée")
                return DayIndexingResult(
                    int(existing["event_count"]),
                    int(existing["video_part_count"]),
                    int(existing["total_video_duration_ms"]),
                    True,
                )
        finally:
            connection.close()

        json_files = find_video_part_json_files(day_folder)
        video_parts: list[VideoPart] = []
        for position, json_path in enumerate(json_files, start=1):
            if is_cancelled():
                raise IndexingCancelledError
            progress_callback(position - 1, len(json_files), json_path.name)
            try:
                video_parts.append(parse_video_part_json(json_path))
            except IgnoredJsonRecordError as error:
                LOGGER.info("%s : %s", json_path, error)

        events = build_events(video_parts)
        part_count = sum(len(event.parts) for event in events)
        duration_ms = round(sum(p.duration_seconds for e in events for p in e.parts) * 1000)
        now = datetime.now().astimezone()
        connection = open_database(database_path)
        try:
            station_id = int(connection.execute("SELECT id FROM stations LIMIT 1").fetchone()["id"])
            with connection:
                day_id = DayRepository(connection).upsert(
                    station_id,
                    day_date,
                    day_folder.relative_to(station_folder),
                    len(events),
                    part_count,
                    duration_ms,
                    events[0].event_start_time.isoformat(timespec="milliseconds")
                    if events
                    else None,
                    events[-1].parts[-1].video_end_time.isoformat(timespec="milliseconds")
                    if events
                    else None,
                    now,
                    signature,
                    json_count,
                )
                EventRepository(connection).synchronize_day_events(
                    day_id, station_folder, events, now
                )
        finally:
            connection.close()
        progress_callback(len(json_files), len(json_files), "Indexation terminée")
        return DayIndexingResult(len(events), part_count, duration_ms, False)
