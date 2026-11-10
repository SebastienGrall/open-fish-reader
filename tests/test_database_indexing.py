from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from open_fish_reader.database.connection import open_database
from open_fish_reader.database.repositories.day_repository import DayRepository
from open_fish_reader.database.repositories.event_repository import EventRepository
from open_fish_reader.database.repositories.station_repository import StationRepository
from open_fish_reader.database.schema import create_initial_schema
from open_fish_reader.indexing.indexing_service import index_day
from open_fish_reader.indexing.station_scanner import scan_station_identity
from open_fish_reader.version import APP_VERSION


def test_index_station_data_into_sqlite(tmp_path: Path) -> None:
    station_folder = tmp_path / "station"
    videos_folder = station_folder / "2026-11-08" / "videos"
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
    json_path = videos_folder / video_name.replace(".mp4", ".json")
    json_path.write_text(json.dumps(metadata), encoding="utf-8")

    database_path = tmp_path / "test.sqlite"
    connection = open_database(database_path)
    now = datetime.now().astimezone()
    create_initial_schema(connection, APP_VERSION, now.isoformat(timespec="milliseconds"))

    station = scan_station_identity(station_folder)
    events = index_day(station_folder / "2026-11-08")
    with connection:
        station_id = StationRepository(connection).upsert(station, now)
        day_id = DayRepository(connection).upsert(
            station_id,
            date(2026, 11, 8),
            Path("2026-11-08"),
            1,
            1,
            661,
            metadata["event_start_time"],
            metadata["video_end_time"],
            now,
        )
        EventRepository(connection).synchronize_day_events(
            day_id,
            station_folder,
            events,
            now,
        )

    assert connection.execute("SELECT COUNT(*) FROM stations").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM days").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM video_parts").fetchone()[0] == 1
    connection.close()
