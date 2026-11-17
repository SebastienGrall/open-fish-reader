from __future__ import annotations

import sqlite3

REFERENCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS development_stages (
    stage_code TEXT PRIMARY KEY,
    stage_label TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS taxon_reference (
    id INTEGER PRIMARY KEY,
    reference_uuid TEXT NOT NULL UNIQUE,
    source_tax_id INTEGER,
    tax_code TEXT NOT NULL UNIQUE CHECK (length(tax_code) BETWEEN 1 AND 10),
    stage_code TEXT REFERENCES development_stages(stage_code) ON DELETE RESTRICT,
    common_name TEXT NOT NULL,
    sandre_code TEXT,
    scientific_name TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taxa (
    id INTEGER PRIMARY KEY,
    taxon_uuid TEXT NOT NULL UNIQUE,
    reference_id INTEGER REFERENCES taxon_reference(id) ON DELETE RESTRICT,
    tax_code TEXT NOT NULL UNIQUE CHECK (length(tax_code) BETWEEN 1 AND 10),
    stage_code TEXT REFERENCES development_stages(stage_code) ON DELETE RESTRICT,
    common_name TEXT NOT NULL,
    sandre_code TEXT,
    scientific_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    keyboard_shortcut TEXT UNIQUE,
    display_order INTEGER NOT NULL DEFAULT 0,
    source_type TEXT NOT NULL DEFAULT 'reference'
        CHECK (source_type IN ('reference', 'custom', 'csv')),
    is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_taxa_active_order
    ON taxa(is_active, is_archived, display_order, tax_code);
"""


def create_taxon_reference_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(REFERENCE_SCHEMA)
