from datetime import UTC, datetime

from open_fish_reader.core.constants import (
    DATABASE_SCHEMA_VERSION,
)
from open_fish_reader.database.connection import (
    open_database,
)
from open_fish_reader.database.schema import (
    create_initial_schema,
)


def test_fresh_database_reaches_current_schema(
    tmp_path,
) -> None:
    database_path = tmp_path / "fresh.sqlite"

    connection = open_database(database_path)

    create_initial_schema(
        connection,
        "test",
        datetime.now(UTC).isoformat(timespec="milliseconds"),
    )

    version = connection.execute(
        """
        SELECT database_schema_version
        FROM database_metadata
        WHERE id = 1
        """
    ).fetchone()[0]

    taxa_columns = {row["name"] for row in connection.execute("PRAGMA table_info(taxa)").fetchall()}

    passage_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(passages)").fetchall()
    }

    assert version == DATABASE_SCHEMA_VERSION

    assert {
        "reference_id",
        "stage_code",
        "source_type",
        "is_archived",
    } <= taxa_columns

    assert {
        "length_pixels",
        "calibration_id",
        "measurement_method",
    } <= passage_columns

    measurement_points_table = connection.execute(
        """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name =
                'passage_measurement_points'
            """
    ).fetchone()

    assert measurement_points_table is not None

    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]

    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()

    assert integrity == "ok"
    assert foreign_key_errors == []

    connection.close()
