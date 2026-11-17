from datetime import UTC, datetime
from pathlib import Path

import pytest

from open_fish_reader.database.connection import (
    open_database,
)
from open_fish_reader.database.repositories.taxon_repository import (
    TaxonRepository,
)
from open_fish_reader.services.taxon_reference_service import (
    TaxonReferenceService,
)


def test_duplicate_active_shortcuts_are_rejected(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "config.sqlite"

    connection = open_database(database_path)

    try:
        connection.execute(
            """
            CREATE TABLE stations (
                id INTEGER PRIMARY KEY
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    TaxonReferenceService().initialize(database_path)

    connection = open_database(database_path)

    try:
        rows = connection.execute(
            """
            SELECT id
            FROM taxa
            WHERE tax_code IN ('AGJ', 'AGG')
            ORDER BY tax_code
            """
        ).fetchall()

        assert len(rows) == 2

        first_id = int(rows[0]["id"])
        second_id = int(rows[1]["id"])

        repository = TaxonRepository(connection)

        with (
            pytest.raises(
                ValueError,
                match="même raccourci",
            ),
            connection,
        ):
            repository.save_configuration(
                (
                    (
                        first_id,
                        True,
                        1,
                        "A",
                    ),
                    (
                        second_id,
                        True,
                        2,
                        "A",
                    ),
                ),
                datetime.now(UTC),
            )

    finally:
        connection.close()
