from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path


class DayRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert(
        self,
        station_id: int,
        day_date: date,
        relative_folder: Path,
        event_count: int,
        video_part_count: int,
        total_video_duration_ms: int,
        first_event_time: str | None,
        last_event_time: str | None,
        now: datetime,
    ) -> int:
        self.connection.execute(
            """
            INSERT INTO days (
                station_id,
                day_date,
                relative_folder,
                event_count,
                video_part_count,
                total_video_duration_ms,
                first_event_time,
                last_event_time,
                last_indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(station_id, day_date) DO UPDATE SET
                relative_folder = excluded.relative_folder,
                event_count = excluded.event_count,
                video_part_count = excluded.video_part_count,
                total_video_duration_ms = excluded.total_video_duration_ms,
                first_event_time = excluded.first_event_time,
                last_event_time = excluded.last_event_time,
                last_indexed_at = excluded.last_indexed_at
            """,
            (
                station_id,
                day_date.isoformat(),
                relative_folder.as_posix(),
                event_count,
                video_part_count,
                total_video_duration_ms,
                first_event_time,
                last_event_time,
                now.isoformat(timespec="milliseconds"),
            ),
        )
        row = self.connection.execute(
            "SELECT id FROM days WHERE station_id = ? AND day_date = ?",
            (station_id, day_date.isoformat()),
        ).fetchone()
        if row is None:
            raise RuntimeError("La journée n'a pas pu être enregistrée.")
        return int(row["id"])

    def list_all(self, station_id: int) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT * FROM days
                WHERE station_id = ?
                ORDER BY day_date
                """,
                (station_id,),
            ).fetchall()
        )
