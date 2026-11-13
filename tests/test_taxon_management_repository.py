from datetime import UTC, datetime
from pathlib import Path

from open_fish_reader.database.catalog_schema import create_catalog_schema
from open_fish_reader.database.connection import open_database
from open_fish_reader.database.migration_v5 import migrate_taxa_to_v5
from open_fish_reader.database.repositories.taxon_management_repository import (
    TaxonManagementRepository,
)


def test_custom_taxon_can_be_created_and_archived(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "taxa.sqlite")
    create_catalog_schema(connection)
    migrate_taxa_to_v5(connection)
    repository = TaxonManagementRepository(connection)
    now = datetime.now(UTC)
    with connection:
        taxon_id = repository.create_custom(
            tax_code="TEST",
            common_name="Poisson test",
            scientific_name="Piscis testus",
            sandre_code=None,
            stage_code=5,
            stage_label="adulte",
            is_active=True,
            display_order=1,
            keyboard_shortcut="T",
            now=now,
        )
    assert repository.get(taxon_id) is not None
    with connection:
        repository.archive(taxon_id, now)
    row = connection.execute(
        "SELECT is_archived, is_active FROM taxa WHERE id = ?", (taxon_id,)
    ).fetchone()
    assert tuple(row) == (1, 0)
    connection.close()
