from __future__ import annotations

import sqlite3


def migrate_to_v8(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(passages)").fetchall()}
    additions = {
        "length_pixels": "REAL CHECK (length_pixels IS NULL OR length_pixels > 0)",
        "calibration_id": ("INTEGER REFERENCES size_calibrations(id) ON DELETE RESTRICT"),
        "measurement_method": (
            "TEXT NOT NULL DEFAULT 'not_measured' "
            "CHECK (measurement_method IN "
            "('not_measured', 'manual', 'polyline_calibration'))"
        ),
    }
    for name, declaration in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE passages ADD COLUMN {name} {declaration}")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS passage_measurement_points (
            id INTEGER PRIMARY KEY,
            passage_id INTEGER NOT NULL
                REFERENCES passages(id) ON DELETE CASCADE,
            point_order INTEGER NOT NULL CHECK (point_order >= 0),
            x REAL NOT NULL,
            y REAL NOT NULL,
            UNIQUE(passage_id, point_order)
        );
        CREATE INDEX IF NOT EXISTS idx_measurement_points_passage
            ON passage_measurement_points(passage_id, point_order);
        """
    )
