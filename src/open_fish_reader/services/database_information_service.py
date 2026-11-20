from __future__ import annotations

from pathlib import Path

from ..database.connection import open_database
from ..domain.database_information import DatabaseInformation


class DatabaseInformationService:
    def read(self, database_path: Path) -> DatabaseInformation:
        connection = open_database(database_path)
        try:
            row = connection.execute(
                """
                SELECT
                    database_schema_version,
                    created_with_app_version,
                    last_opened_with_app_version,
                    created_at,
                    updated_at
                FROM database_metadata
                WHERE id = 1
                """
            ).fetchone()
            if row is None:
                raise RuntimeError("Les métadonnées de la base sont introuvables.")
            return DatabaseInformation(
                database_path=database_path,
                schema_version=int(row["database_schema_version"]),
                created_with_app_version=str(row["created_with_app_version"]),
                last_opened_with_app_version=str(row["last_opened_with_app_version"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
        finally:
            connection.close()
