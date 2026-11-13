from __future__ import annotations

import sqlite3

CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS taxa (
    id INTEGER PRIMARY KEY,
    taxon_uuid TEXT NOT NULL UNIQUE,
    source_tax_id INTEGER,

    tax_code TEXT NOT NULL UNIQUE,

    stage_code INTEGER NOT NULL,
    stage_label TEXT NOT NULL,

    common_name TEXT NOT NULL,
    sandre_code TEXT,
    scientific_name TEXT NOT NULL,

    is_active INTEGER NOT NULL
        DEFAULT 0
        CHECK (is_active IN (0, 1)),

    keyboard_shortcut TEXT,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    source_type TEXT NOT NULL
        DEFAULT 'catalog'
        CHECK (
            source_type IN (
                'catalog',
                'custom'
            )
        ),

    is_archived INTEGER NOT NULL
        DEFAULT 0
        CHECK (is_archived IN (0, 1)),

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE(keyboard_shortcut)
);

CREATE INDEX IF NOT EXISTS idx_taxa_active_order
    ON taxa(is_active, display_order, tax_code);

CREATE TABLE IF NOT EXISTS size_calibrations (
    id INTEGER PRIMARY KEY,
    calibration_uuid TEXT NOT NULL UNIQUE,
    station_id INTEGER NOT NULL REFERENCES stations(id) ON DELETE RESTRICT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    near_mm_per_pixel REAL NOT NULL CHECK (near_mm_per_pixel > 0),
    middle_mm_per_pixel REAL NOT NULL CHECK (middle_mm_per_pixel > 0),
    far_mm_per_pixel REAL NOT NULL CHECK (far_mm_per_pixel > 0),
    comment TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE INDEX IF NOT EXISTS idx_calibrations_station_period
    ON size_calibrations(station_id, valid_from, valid_to);
"""


def create_catalog_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(CATALOG_SCHEMA)
