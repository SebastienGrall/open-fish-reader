from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..core.database_naming import station_database_name
from ..core.paths import get_app_paths
from ..database.connection import open_database
from ..database.repositories.day_repository import DayRepository
from ..database.repositories.station_repository import StationRepository
from ..database.schema import create_initial_schema
from ..domain.station import Station
from ..indexing.day_scanner import find_day_folders
from ..indexing.station_scanner import scan_station_identity
from ..version import APP_VERSION


@dataclass(slots=True)
class OpenedStation:
    station: Station
    database_path: Path
    connection: sqlite3.Connection
    day_folders: list[Path]

    @property
    def detected_day_count(self) -> int:
        return len(self.day_folders)


class StationService:
    def open_station(
        self,
        station_folder: Path,
    ) -> OpenedStation:
        station_folder = station_folder.resolve()

        station = scan_station_identity(station_folder)

        database_name = station_database_name(
            station.slug,
            station.source_folder,
        )

        database_path = get_app_paths().databases / database_name

        connection = open_database(database_path)

        now = datetime.now().astimezone()

        try:
            create_initial_schema(
                connection,
                APP_VERSION,
                now.isoformat(timespec="milliseconds"),
            )

            day_folders = find_day_folders(station_folder)

            with connection:
                station_id = StationRepository(connection).upsert(
                    station,
                    now,
                )

                day_repository = DayRepository(connection)

                for day_folder in day_folders:
                    day_date = datetime.strptime(
                        day_folder.name,
                        "%Y-%m-%d",
                    ).date()

                    day_repository.upsert(
                        station_id=station_id,
                        day_date=day_date,
                        relative_folder=day_folder.relative_to(station_folder),
                        event_count=0,
                        video_part_count=0,
                        total_video_duration_ms=0,
                        first_event_time=None,
                        last_event_time=None,
                        now=now,
                    )

            return OpenedStation(
                station=station,
                database_path=database_path,
                connection=connection,
                day_folders=day_folders,
            )

        except Exception:
            connection.close()
            raise
