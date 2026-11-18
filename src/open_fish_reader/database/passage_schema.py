from __future__ import annotations

import sqlite3

PASSAGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS passages (
    id INTEGER PRIMARY KEY,
    passage_uuid TEXT NOT NULL UNIQUE,
    station_id INTEGER NOT NULL REFERENCES stations(id) ON DELETE RESTRICT,
    video_part_id INTEGER NOT NULL REFERENCES video_parts(id) ON DELETE RESTRICT,
    taxon_id INTEGER NOT NULL REFERENCES taxa(id) ON DELETE RESTRICT,
    frame_number INTEGER NOT NULL CHECK (frame_number >= 0),
    position_ms INTEGER NOT NULL CHECK (position_ms >= 0),
    observed_at TEXT NOT NULL,
    individual_count INTEGER NOT NULL DEFAULT 1
        CHECK (individual_count BETWEEN 1 AND 99),
    direction INTEGER NOT NULL CHECK (direction IN (-1, 0, 1)),
    confidence TEXT NOT NULL DEFAULT 'certain'
        CHECK (confidence IN ('certain', 'probable', 'uncertain')),
    needs_review INTEGER NOT NULL DEFAULT 0 CHECK (needs_review IN (0, 1)),
    glass_position TEXT NOT NULL DEFAULT 'middle'
        CHECK (glass_position IN ('near', 'middle', 'far')),
    length_mm INTEGER CHECK (length_mm IS NULL OR length_mm > 0),
    comment TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_passages_video_part_frame
    ON passages(video_part_id, frame_number);
CREATE INDEX IF NOT EXISTS idx_passages_station_time
    ON passages(station_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_passages_taxon_time
    ON passages(taxon_id, observed_at);
"""


def create_passage_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(PASSAGE_SCHEMA)
