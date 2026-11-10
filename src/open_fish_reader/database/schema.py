import sqlite3

from ..core.constants import DATABASE_SCHEMA_VERSION

SCHEMA = """
CREATE TABLE IF NOT EXISTS database_metadata(id INTEGER PRIMARY KEY CHECK(id=1),database_schema_version INTEGER NOT NULL,created_with_app_version TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stations(id INTEGER PRIMARY KEY,station_name TEXT NOT NULL,station_slug TEXT NOT NULL,source_folder TEXT NOT NULL,extraction_folder TEXT);
CREATE TABLE IF NOT EXISTS days(id INTEGER PRIMARY KEY,station_id INTEGER NOT NULL REFERENCES stations(id),day_date TEXT NOT NULL,relative_folder TEXT NOT NULL,UNIQUE(station_id,day_date));
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,day_id INTEGER NOT NULL REFERENCES days(id),source_event_id TEXT NOT NULL UNIQUE,event_start_time TEXT NOT NULL,event_detection_time TEXT NOT NULL,review_status TEXT NOT NULL DEFAULT 'unviewed');
CREATE TABLE IF NOT EXISTS video_parts(id INTEGER PRIMARY KEY,event_id INTEGER NOT NULL REFERENCES events(id),part_number INTEGER NOT NULL CHECK(part_number>=1),video_relative_path TEXT NOT NULL,json_relative_path TEXT NOT NULL,video_start_time TEXT NOT NULL,video_end_time TEXT NOT NULL,declared_frame_count INTEGER NOT NULL,declared_fps REAL NOT NULL,frame_width INTEGER NOT NULL,frame_height INTEGER NOT NULL,UNIQUE(event_id,part_number));
"""


def create_initial_schema(c: sqlite3.Connection, version: str) -> None:
    c.executescript(SCHEMA)
    c.execute(
        "INSERT OR IGNORE INTO database_metadata VALUES(1,?,?)", (DATABASE_SCHEMA_VERSION, version)
    )
    c.commit()
