from __future__ import annotations

import sqlite3
from datetime import datetime

from ...domain.station import Station


class StationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert(self, station: Station, now: datetime) -> int:
        now_iso = now.isoformat(timespec="milliseconds")
        row = self.connection.execute("SELECT id FROM stations LIMIT 1").fetchone()

        if row is None:
            cursor = self.connection.execute(
                """
                INSERT INTO stations (
                    station_name,
                    station_slug,
                    source_folder,
                    extraction_folder,
                    created_at,
                    last_opened_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    station.name,
                    station.slug,
                    str(station.source_folder),
                    str(station.extraction_folder) if station.extraction_folder else None,
                    now_iso,
                    now_iso,
                ),
            )
            station_id = int(cursor.lastrowid)
        else:
            station_id = int(row["id"])
            self.connection.execute(
                """
                UPDATE stations
                SET station_name = ?,
                    station_slug = ?,
                    source_folder = ?,
                    extraction_folder = ?,
                    last_opened_at = ?
                WHERE id = ?
                """,
                (
                    station.name,
                    station.slug,
                    str(station.source_folder),
                    str(station.extraction_folder) if station.extraction_folder else None,
                    now_iso,
                    station_id,
                ),
            )

        station.id = station_id
        return station_id
