from __future__ import annotations

import sqlite3

from .passage_schema import create_passage_schema


def migrate_to_v7(connection: sqlite3.Connection) -> None:
    create_passage_schema(connection)
