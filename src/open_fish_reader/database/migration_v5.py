from __future__ import annotations

import sqlite3


def migrate_taxa_to_v5(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(taxa)").fetchall()}
    if "source_type" not in columns:
        connection.execute(
            "ALTER TABLE taxa ADD COLUMN source_type TEXT NOT NULL DEFAULT 'catalog'"
        )
    if "is_archived" not in columns:
        connection.execute("ALTER TABLE taxa ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0")
