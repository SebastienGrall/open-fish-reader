from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from ...domain.event import Event


class EventRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def synchronize_day_events(
        self, day_id: int, station_folder: Path, events: list[Event], now: datetime
    ) -> None:
        now_iso = now.isoformat(timespec="milliseconds")
        retained_event_ids: set[int] = set()

        for event in events:
            first_part, last_part = event.parts[0], event.parts[-1]
            duration_ms = round(sum(p.duration_seconds for p in event.parts) * 1000)
            existing = self.connection.execute(
                "SELECT id FROM events WHERE day_id = ? AND source_event_id = ?",
                (day_id, event.source_event_id),
            ).fetchone()
            if existing is None:
                cursor = self.connection.execute(
                    """INSERT INTO events (
                        day_id, source_event_id, station_name, event_start_time,
                        event_detection_time, first_video_start_time,
                        last_video_end_time, part_count, total_frame_count,
                        total_duration_ms, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            else:
                event_id = int(existing["id"])
                self.connection.execute(
                    """UPDATE events SET station_name = ?, event_start_time = ?,
                    event_detection_time = ?, first_video_start_time = ?,
                    last_video_end_time = ?, part_count = ?, total_frame_count = ?,
                    total_duration_ms = ?, updated_at = ? WHERE id = ?""",
                    (
                        event.station_name,
                        event.event_start_time.isoformat(timespec="milliseconds"),
                        event.event_detection_time.isoformat(timespec="milliseconds"),
                        first_part.video_start_time.isoformat(timespec="milliseconds"),
                        last_part.video_end_time.isoformat(timespec="milliseconds"),
                        len(event.parts),
                        event.total_frame_count,
                        duration_ms,
                        now_iso,
                        event_id,
                    ),
                )
            event.id = event_id
            retained_event_ids.add(event_id)
            self._synchronize_parts(event_id, station_folder, event, now_iso)

        existing_rows = self.connection.execute(
            "SELECT id FROM events WHERE day_id = ?", (day_id,)
        ).fetchall()
        for row in existing_rows:
            event_id = int(row["id"])
            if event_id not in retained_event_ids:
                self.connection.execute("DELETE FROM video_parts WHERE event_id = ?", (event_id,))
                self.connection.execute("DELETE FROM events WHERE id = ?", (event_id,))

    def _synchronize_parts(
        self, event_id: int, station_folder: Path, event: Event, now_iso: str
    ) -> None:
        retained_numbers: set[int] = set()
        for part in event.parts:
            retained_numbers.add(part.part_number)
            video_relative = part.video_path.relative_to(station_folder).as_posix()
            json_relative = part.json_path.relative_to(station_folder).as_posix()
            exists = part.video_path.exists()
            stat = part.video_path.stat() if exists else None
            modified = (
                datetime.fromtimestamp(stat.st_mtime)
                .astimezone()
                .isoformat(timespec="milliseconds")
                if stat
                else None
            )
            self.connection.execute(
                """INSERT INTO video_parts (
                    event_id, part_number, video_relative_path, json_relative_path,
                    video_file_name, json_file_name, json_schema_version, record_type,
                    video_start_time, video_end_time, declared_frame_count,
                    declared_fps, frame_width, frame_height, file_size,
                    file_modified_at, media_status, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id, part_number) DO UPDATE SET
                    video_relative_path = excluded.video_relative_path,
                    json_relative_path = excluded.json_relative_path,
                    video_file_name = excluded.video_file_name,
                    json_file_name = excluded.json_file_name,
                    json_schema_version = excluded.json_schema_version,
                    record_type = excluded.record_type,
                    video_start_time = excluded.video_start_time,
                    video_end_time = excluded.video_end_time,
                    declared_frame_count = excluded.declared_frame_count,
                    declared_fps = excluded.declared_fps,
                    frame_width = excluded.frame_width,
                    frame_height = excluded.frame_height,
                    file_size = excluded.file_size,
                    file_modified_at = excluded.file_modified_at,
                    media_status = excluded.media_status,
                    indexed_at = excluded.indexed_at""",
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
                    stat.st_size if stat else None,
                    modified,
                    "available" if exists else "video_missing",
                    now_iso,
                ),
            )

        rows = self.connection.execute(
            "SELECT id, part_number FROM video_parts WHERE event_id = ?", (event_id,)
        ).fetchall()
        for row in rows:
            if int(row["part_number"]) not in retained_numbers:
                self.connection.execute("DELETE FROM video_parts WHERE id = ?", (row["id"],))
