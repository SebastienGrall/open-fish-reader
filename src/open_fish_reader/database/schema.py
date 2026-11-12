from __future__ import annotations

import sqlite3

from ..core.constants import DATABASE_SCHEMA_VERSION
from .migrations import migrate_database

SCHEMA = """
CREATE TABLE IF NOT EXISTS database_metadata (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    database_schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_with_app_version TEXT NOT NULL,
    last_opened_with_app_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stations (
    id INTEGER PRIMARY KEY, station_name TEXT NOT NULL, station_slug TEXT NOT NULL,
    source_folder TEXT NOT NULL, extraction_folder TEXT, created_at TEXT NOT NULL,
    last_opened_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS days (
    id INTEGER PRIMARY KEY,
    station_id INTEGER NOT NULL REFERENCES stations(id) ON DELETE RESTRICT,
    day_date TEXT NOT NULL, relative_folder TEXT NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    video_part_count INTEGER NOT NULL DEFAULT 0,
    total_video_duration_ms INTEGER NOT NULL DEFAULT 0,
    anomaly_count INTEGER NOT NULL DEFAULT 0,
    first_event_time TEXT, last_event_time TEXT, last_indexed_at TEXT NOT NULL,
    source_signature TEXT, source_json_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(station_id, day_date)
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    day_id INTEGER NOT NULL REFERENCES days(id) ON DELETE RESTRICT,
    source_event_id TEXT NOT NULL, station_name TEXT NOT NULL,
    event_start_time TEXT NOT NULL, event_detection_time TEXT NOT NULL,
    first_video_start_time TEXT NOT NULL, last_video_end_time TEXT NOT NULL,
    part_count INTEGER NOT NULL, total_frame_count INTEGER NOT NULL,
    total_duration_ms INTEGER NOT NULL, review_status TEXT NOT NULL DEFAULT 'unviewed',
    last_viewed_part_id INTEGER, last_viewed_frame INTEGER,
    last_viewed_position_ms INTEGER,
    needs_review INTEGER NOT NULL DEFAULT 0 CHECK (needs_review IN (0, 1)),
    has_anomaly INTEGER NOT NULL DEFAULT 0 CHECK (has_anomaly IN (0, 1)),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE(day_id, source_event_id)
);
CREATE TABLE IF NOT EXISTS video_parts (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL
        REFERENCES events(id)
        ON DELETE RESTRICT,
    part_number INTEGER NOT NULL
        CHECK (part_number >= 1),

    video_relative_path TEXT NOT NULL,
    json_relative_path TEXT NOT NULL,
    video_file_name TEXT NOT NULL,
    json_file_name TEXT NOT NULL,

    json_schema_version INTEGER NOT NULL,
    record_type TEXT NOT NULL,

    video_start_time TEXT NOT NULL,
    video_end_time TEXT NOT NULL,

    declared_frame_count INTEGER NOT NULL
        CHECK (declared_frame_count >= 0),
    declared_fps REAL NOT NULL
        CHECK (declared_fps > 0),

    frame_width INTEGER NOT NULL
        CHECK (frame_width > 0),
    frame_height INTEGER NOT NULL
        CHECK (frame_height > 0),

    file_size INTEGER,
    file_modified_at TEXT,
    media_status TEXT NOT NULL
        DEFAULT 'available',
    indexed_at TEXT NOT NULL,

    review_status TEXT NOT NULL
        DEFAULT 'unread',
    first_opened_at TEXT,
    last_opened_at TEXT,
    last_viewed_frame INTEGER,
    completed_at TEXT,
    observation_count INTEGER NOT NULL
        DEFAULT 0
        CHECK (observation_count >= 0),
    error_message TEXT,

    UNIQUE(event_id, part_number)
);
CREATE INDEX IF NOT EXISTS idx_days_station_date ON days(station_id, day_date);
CREATE INDEX IF NOT EXISTS idx_events_day_start ON events(day_id, event_start_time);
CREATE INDEX IF NOT EXISTS idx_video_parts_event_part ON video_parts(event_id, part_number);
"""


def create_initial_schema(connection: sqlite3.Connection, app_version: str, now_iso: str) -> None:
    connection.executescript(SCHEMA)
    connection.execute(
        """
        INSERT OR IGNORE INTO database_metadata (
            id, database_schema_version, created_at, updated_at,
            created_with_app_version, last_opened_with_app_version
        ) VALUES (1, ?, ?, ?, ?, ?)
        """,
        (DATABASE_SCHEMA_VERSION, now_iso, now_iso, app_version, app_version),
    )
    migrate_database(connection)
    connection.execute(
        """UPDATE database_metadata
        SET updated_at = ?, last_opened_with_app_version = ? WHERE id = 1""",
        (now_iso, app_version),
    )
    connection.commit()
