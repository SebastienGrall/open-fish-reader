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


def test_unchanged_day_reuses_existing_ids(tmp_path: Path) -> None:
    station = tmp_path / "station"
    videos = station / "2026-11-08" / "videos"
    videos.mkdir(parents=True)
    name = "Poses_RG_OFC_20261108_000233_part001.mp4"
    (videos / name).write_bytes(b"fake")
    data = {
        "schema_version": 1,
        "record_type": "video_part",
        "event_id": "Poses_RG_OFC_20261108_000233_993",
        "station_name": "Poses RG OFC",
        "video_file": name,
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
    (videos / name.replace(".mp4", ".json")).write_text(json.dumps(data), encoding="utf-8")
    db = tmp_path / "db.sqlite"
    c = open_database(db)
    now = datetime.now().astimezone()
    create_initial_schema(c, APP_VERSION, now.isoformat(timespec="milliseconds"))
    model = scan_station_identity(station)
    with c:
        StationRepository(c).upsert(model, now)
    c.close()
    service = DayIndexingService()
    day = station / "2026-11-08"
    first = service.index_day(db, station, day, lambda *_: None, lambda: False)
    c = open_database(db)
    event_id = int(c.execute("SELECT id FROM events").fetchone()["id"])
    c.close()
    second = service.index_day(db, station, day, lambda *_: None, lambda: False)
    c = open_database(db)
    same_id = int(c.execute("SELECT id FROM events").fetchone()["id"])
    c.close()
    assert first.skipped is False
    assert second.skipped is True
    assert event_id == same_id
