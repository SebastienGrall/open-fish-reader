from datetime import UTC, datetime
from pathlib import Path

from open_fish_reader.database.connection import open_database
from open_fish_reader.database.migrations import migrate_database
from open_fish_reader.database.repositories.video_part_status_repository import (
    VideoPartStatusRepository,
)


def create_database(path: Path):
    connection = open_database(path)
    connection.executescript(
        """
        CREATE TABLE database_metadata (
            id INTEGER PRIMARY KEY,
            database_schema_version INTEGER NOT NULL
        );
        INSERT INTO database_metadata VALUES (1, 2);
        CREATE TABLE video_parts (
            id INTEGER PRIMARY KEY,
            event_id INTEGER NOT NULL,
            part_number INTEGER NOT NULL,
            video_relative_path TEXT NOT NULL,
            json_relative_path TEXT NOT NULL,
            video_file_name TEXT NOT NULL,
            json_file_name TEXT NOT NULL,
            json_schema_version INTEGER NOT NULL,
            record_type TEXT NOT NULL,
            video_start_time TEXT NOT NULL,
            video_end_time TEXT NOT NULL,
            declared_frame_count INTEGER NOT NULL,
            declared_fps REAL NOT NULL,
            frame_width INTEGER NOT NULL,
            frame_height INTEGER NOT NULL,
            media_status TEXT NOT NULL,
            indexed_at TEXT NOT NULL
        );
        INSERT INTO video_parts VALUES (
            1, 1, 1, 'video.mp4', 'video.json', 'video.mp4', 'video.json',
            1, 'video_part', '2026-01-01T00:00:00+00:00',
            '2026-01-01T00:00:01+00:00', 10, 10.0, 640, 540,
            'available', '2026-01-01T00:00:00+00:00'
        );
        """
    )
    connection.commit()
    return connection


def test_migration_and_status_lifecycle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "open_fish_reader.database.migrations.DATABASE_SCHEMA_VERSION",
        3,
    )
    connection = create_database(tmp_path / "status.sqlite")
    migrate_database(connection)
    repository = VideoPartStatusRepository(connection)
    now = datetime.now(UTC)

    with connection:
        repository.mark_opened(1, now)
    row = connection.execute("SELECT * FROM video_parts WHERE id = 1").fetchone()
    assert row["review_status"] == "in_progress"
    assert row["first_opened_at"] is not None

    with connection:
        repository.mark_completed(1, 9, now)
    row = connection.execute("SELECT * FROM video_parts WHERE id = 1").fetchone()
    assert row["review_status"] == "read"
    assert row["last_viewed_frame"] == 9
    assert row["completed_at"] is not None
    connection.close()
