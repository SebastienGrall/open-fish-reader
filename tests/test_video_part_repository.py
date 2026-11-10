from __future__ import annotations

from datetime import datetime
from pathlib import Path

from open_fish_reader.database.connection import open_database
from open_fish_reader.database.repositories.video_part_repository import VideoPartRepository
from open_fish_reader.database.schema import create_initial_schema
from open_fish_reader.version import APP_VERSION


def test_lists_parts_in_chronological_order(tmp_path: Path) -> None:
    db = tmp_path / "test.sqlite"
    connection = open_database(db)
    now = datetime.now().astimezone().isoformat(timespec="milliseconds")
    create_initial_schema(connection, APP_VERSION, now)
    with connection:
        station_id = connection.execute(
            "INSERT INTO stations (station_name, station_slug, source_folder, created_at, last_opened_at) VALUES (?, ?, ?, ?, ?)",
            ("Station", "Station", str(tmp_path), now, now),
        ).lastrowid
        day_id = connection.execute(
            "INSERT INTO days (station_id, day_date, relative_folder, last_indexed_at) VALUES (?, ?, ?, ?)",
            (station_id, "2026-11-08", "2026-11-08", now),
        ).lastrowid
        event_id = connection.execute(
            """INSERT INTO events (day_id, source_event_id, station_name, event_start_time, event_detection_time, first_video_start_time, last_video_end_time, part_count, total_frame_count, total_duration_ms, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (day_id, "event", "Station", now, now, now, now, 2, 10, 500, now, now),
        ).lastrowid
        for part_number in (2, 1):
            connection.execute(
                """INSERT INTO video_parts (event_id, part_number, video_relative_path, json_relative_path, video_file_name, json_file_name, json_schema_version, record_type, video_start_time, video_end_time, declared_frame_count, declared_fps, frame_width, frame_height, media_status, indexed_at) VALUES (?, ?, ?, ?, ?, ?, 1, 'video_part', ?, ?, 5, 20.0, 640, 540, 'available', ?)""",
                (
                    event_id,
                    part_number,
                    f"day/videos/p{part_number}.mp4",
                    f"day/videos/p{part_number}.json",
                    f"p{part_number}.mp4",
                    f"p{part_number}.json",
                    now,
                    now,
                    now,
                ),
            )
    parts = VideoPartRepository(connection).list_for_day("2026-11-08", tmp_path)
    assert [part.part_number for part in parts] == [1, 2]
    connection.close()
