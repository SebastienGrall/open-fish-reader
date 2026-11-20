import sqlite3

from open_fish_reader.services.database_information_service import (
    DatabaseInformationService,
)


def test_reads_database_metadata(tmp_path) -> None:
    path = tmp_path / "metadata.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE database_metadata (
            id INTEGER PRIMARY KEY,
            database_schema_version INTEGER,
            created_at TEXT,
            updated_at TEXT,
            created_with_app_version TEXT,
            last_opened_with_app_version TEXT
        )
        """
    )
    connection.execute(
        "INSERT INTO database_metadata VALUES (1, 8, '2026-01-01T09:00:00+01:00', "
        "'2026-11-20T09:00:00+01:00', '0.5.0', '0.9.0')"
    )
    connection.commit()
    connection.close()

    information = DatabaseInformationService().read(path)
    assert information.schema_version == 8
    assert information.created_with_app_version == "0.5.0"
    assert information.last_opened_with_app_version == "0.9.0"
