from datetime import UTC, datetime
from pathlib import Path

from open_fish_reader.database.connection import (
    open_database,
)
from open_fish_reader.database.repositories.taxon_management_repository import (
    TaxonManagementRepository,
)
from open_fish_reader.database.taxon_reference_schema import (
    create_taxon_reference_schema,
)
from open_fish_reader.database.taxon_reference_seed import (
    DEVELOPMENT_STAGE_SEED,
)


def test_custom_taxon_can_be_created_and_archived(
    tmp_path: Path,
) -> None:
    connection = open_database(tmp_path / "taxa.sqlite")

    # Schéma minimal nécessaire à la clé étrangère
    # de size_calibrations.
    connection.execute(
        """
        CREATE TABLE stations (
            id INTEGER PRIMARY KEY
        )
        """
    )

    create_taxon_reference_schema(connection)

    connection.executemany(
        """
        INSERT INTO development_stages (
            stage_code,
            stage_label,
            display_order,
            is_active
        )
        VALUES (?, ?, ?, 1)
        """,
        [
            (
                code,
                label,
                display_order,
            )
            for display_order, (
                code,
                label,
            ) in enumerate(
                DEVELOPMENT_STAGE_SEED,
                start=1,
            )
        ],
    )

    repository = TaxonManagementRepository(connection)
    now = datetime.now(UTC)

    with connection:
        taxon_id = repository.create_custom(
            tax_code="TEST",
            common_name="Poisson test",
            scientific_name="Piscis testus",
            sandre_code=None,
            stage_code=None,
            is_active=True,
            display_order=1,
            keyboard_shortcut="T",
            now=now,
        )

    taxon = repository.get(taxon_id)

    assert taxon is not None
    assert taxon.tax_code == "TEST"
    assert taxon.stage_code is None
    assert taxon.stage_label is None
    assert taxon.is_active is True

    with connection:
        repository.archive(
            taxon_id,
            now,
        )

    row = connection.execute(
        """
        SELECT
            is_archived,
            is_active,
            keyboard_shortcut
        FROM taxa
        WHERE id = ?
        """,
        (taxon_id,),
    ).fetchone()

    assert row is not None
    assert row["is_archived"] == 1
    assert row["is_active"] == 0
    assert row["keyboard_shortcut"] is None

    connection.close()
