from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from ...domain.event import Event


class EventRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def replace_day_events(
        self,
        day_id: int,
        station_folder: Path,
        events: list[Event],
        now: datetime,
    ) -> None:
        existing = self.connection.execute(
            "SELECT id FROM events WHERE day_id = ?",
            (day_id,),
        ).fetchall()
        for row in existing:
            self.connection.execute(
                "DELETE FROM video_parts WHERE event_id = ?",
                (row["id"],),
            )
        self.connection.execute("DELETE FROM events WHERE day_id = ?", (day_id,))

        now_iso = now.isoformat(timespec="milliseconds")
        for event in events:
            first_part = event.parts[0]
            last_part = event.parts[-1]
            duration_ms = round(sum(part.duration_seconds for part in event.parts) * 1000)
            cursor = self.connection.execute(
                """
                INSERT INTO events (
                    day_id,
                    source_event_id,
                    station_name,
                    event_start_time,
                    event_detection_time,
                    first_video_start_time,
                    last_video_end_time,
                    part_count,
                    total_frame_count,
                    total_duration_ms,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    day_id,
                    event.source_event_id,
                    event.station_name,
                    event.event_start_time.isoformat(timespec="milliseconds"),
                    event.event_detection_time.isoformat(timespec="milliseconds"),
                    first_part.video_start_time.isoformat(timespec="milliseconds"),
                    last_part.video_end_time.isoformat(timespec="milliseconds"),
                    len(event.parts),
                    event.total_frame_count,
                    duration_ms,
                    now_iso,
                    now_iso,
                ),
            )
            event_id = int(cursor.lastrowid)
            event.id = event_id

            for part in event.parts:
                video_relative = part.video_path.relative_to(station_folder).as_posix()
                json_relative = part.json_path.relative_to(station_folder).as_posix()
                file_size = part.video_path.stat().st_size if part.video_path.exists() else None
                modified = (
                    datetime.fromtimestamp(part.video_path.stat().st_mtime)
                    .astimezone()
                    .isoformat(timespec="milliseconds")
                    if part.video_path.exists()
                    else None
                )
                media_status = "available" if part.video_path.exists() else "video_missing"
                self.connection.execute(
                    """
                    INSERT INTO video_parts (
                        event_id,
                        part_number,
                        video_relative_path,
                        json_relative_path,
                        video_file_name,
                        json_file_name,
                        json_schema_version,
                        record_type,
                        video_start_time,
                        video_end_time,
                        declared_frame_count,
                        declared_fps,
                        frame_width,
                        frame_height,
                        file_size,
                        file_modified_at,
                        media_status,
                        indexed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        part.part_number,
                        video_relative,
                        json_relative,
                        part.video_file,
                        part.json_path.name,
                        part.schema_version,
                        part.record_type,
                        part.video_start_time.isoformat(timespec="milliseconds"),
                        part.video_end_time.isoformat(timespec="milliseconds"),
                        part.frame_count,
                        part.recording_fps,
                        part.frame_width,
                        part.frame_height,
                        file_size,
                        modified,
                        media_status,
                        now_iso,
                    ),
                )
