from __future__ import annotations

import sqlite3

from ..core.constants import DATABASE_SCHEMA_VERSION


def migrate_database(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT database_schema_version FROM database_metadata WHERE id = 1"
    ).fetchone()
    if row is None:
        return

    version = int(row["database_schema_version"])
    if version < 2:
        columns = {
            item["name"] for item in connection.execute("PRAGMA table_info(days)").fetchall()
        }
        if "source_signature" not in columns:
            connection.execute("ALTER TABLE days ADD COLUMN source_signature TEXT")
        if "source_json_count" not in columns:
            connection.execute(
                "ALTER TABLE days ADD COLUMN source_json_count INTEGER NOT NULL DEFAULT 0"
            )
        connection.execute(
            "UPDATE database_metadata SET database_schema_version = ? WHERE id = 1",
            (2,),
        )
        connection.commit()
        version = 2

    if version != DATABASE_SCHEMA_VERSION:
        raise RuntimeError(
            f"Version SQLite inattendue : {version}, attendue : {DATABASE_SCHEMA_VERSION}."
        )
