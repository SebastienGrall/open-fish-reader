from __future__ import annotations

import sqlite3

from ..core.constants import (
    DATABASE_SCHEMA_VERSION,
)
from .catalog_schema import (
    create_catalog_schema,
)
from .migration_v5 import migrate_taxa_to_v5


def migrate_database(
    connection: sqlite3.Connection,
) -> None:
    row = connection.execute(
        """
        SELECT database_schema_version
        FROM database_metadata
        WHERE id = 1
        """
    ).fetchone()

    if row is None:
        return

    version = int(row["database_schema_version"])

    if version < 2:
        day_columns = {
            item["name"] for item in connection.execute("PRAGMA table_info(days)").fetchall()
        }

        if "source_signature" not in day_columns:
            connection.execute(
                """
                ALTER TABLE days
                ADD COLUMN source_signature TEXT
                """
            )

        if "source_json_count" not in day_columns:
            connection.execute(
                """
                ALTER TABLE days
                ADD COLUMN source_json_count
                    INTEGER NOT NULL DEFAULT 0
                """
            )

        version = 2

    if version < 3:
        video_part_columns = {
            item["name"] for item in connection.execute("PRAGMA table_info(video_parts)").fetchall()
        }

        additions = {
            "review_status": ("TEXT NOT NULL DEFAULT 'unread'"),
            "first_opened_at": "TEXT",
            "last_opened_at": "TEXT",
            "last_viewed_frame": "INTEGER",
            "completed_at": "TEXT",
            "observation_count": ("INTEGER NOT NULL DEFAULT 0"),
            "error_message": "TEXT",
        }

        for column_name, declaration in additions.items():
            if column_name in video_part_columns:
                continue

            connection.execute(f"ALTER TABLE video_parts ADD COLUMN {column_name} {declaration}")

        version = 3

    if version < 4:
        create_catalog_schema(connection)
        version = 4

    if version < 5:
        migrate_taxa_to_v5(connection)
        version = 5

    connection.execute(
        """
        UPDATE database_metadata
        SET database_schema_version = ?
        WHERE id = 1
        """,
        (version,),
    )

    connection.commit()

    if version != DATABASE_SCHEMA_VERSION:
        raise RuntimeError(
            f"Version SQLite inattendue : {version}, attendue : {DATABASE_SCHEMA_VERSION}."
        )
