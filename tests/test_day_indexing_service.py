from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from open_fish_reader.database.connection import open_database
from open_fish_reader.database.repositories.station_repository import StationRepository
from open_fish_reader.database.schema import create_initial_schema
from open_fish_reader.indexing.station_scanner import scan_station_identity
from open_fish_reader.services.day_indexing_service import DayIndexingService
from open_fish_reader.version import APP_VERSION


def test_day_indexing_service(tmp_path: Path) -> None:
    station_folder = tmp_path / "station"
    day_folder = station_folder / "2026-11-08"
    videos_folder = day_folder / "videos"
    videos_folder.mkdir(parents=True)
    video_name = "Poses_RG_OFC_20261108_000233_part001.mp4"
    (videos_folder / video_name).write_bytes(b"fake-mp4")
    metadata = {
        "schema_version": 1,
        "record_type": "video_part",
        "event_id": "Poses_RG_OFC_20261108_000233_993",
        "station_name": "Poses RG OFC",
        "video_file": video_name,
        "part_number": 1,
        "event_start_time": "2026-11-08T00:02:33.993+01:00",
        "event_detection_time": "2026-11-08T00:02:34.299+01:00",
        "video_start_time": "2026-11-08T00:02:33.993+01:00",
        "video_end_time": "2026-11-08T00:02:34.654+01:00",
        "frame_count": 12,
        "recording_fps": 20.001,
        "frame_width": 640,
        "frame_height": 540,
    }
    (videos_folder / video_name.replace(".mp4", ".json")).write_text(
        json.dumps(metadata), encoding="utf-8"
    )

    database_path = tmp_path / "test.sqlite"
    connection = open_database(database_path)
    now = datetime.now().astimezone()
    create_initial_schema(connection, APP_VERSION, now.isoformat(timespec="milliseconds"))
    station = scan_station_identity(station_folder)
    with connection:
        StationRepository(connection).upsert(station, now)
    connection.close()

    progress: list[tuple[int, int, str]] = []
    result = DayIndexingService().index_day(
        database_path,
        station_folder,
        day_folder,
        lambda current, total, name: progress.append((current, total, name)),
        lambda: False,
    )

    assert result.event_count == 1
    assert result.part_count == 1
    assert result.duration_ms == 661
    assert result.skipped is False
    assert progress
    verify = open_database(database_path)
    assert verify.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert verify.execute("SELECT COUNT(*) FROM video_parts").fetchone()[0] == 1
    verify.close()
