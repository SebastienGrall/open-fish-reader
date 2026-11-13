from datetime import UTC, datetime
from pathlib import Path

import pytest

from open_fish_reader.database.catalog_schema import create_catalog_schema
from open_fish_reader.database.connection import open_database
from open_fish_reader.database.repositories.taxon_repository import TaxonRepository


def test_duplicate_active_shortcuts_are_rejected(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "config.sqlite")
    create_catalog_schema(connection)
    repository = TaxonRepository(connection)
    now = datetime.now(UTC)
    with connection:
        repository.upsert_seed(
            source_tax_id=1,
            tax_code="AAA",
            stage_code=5,
            stage_label="adulte",
            common_name="A",
            sandre_code=None,
            scientific_name="A a",
            display_order=1,
            now=now,
        )
        repository.upsert_seed(
            source_tax_id=2,
            tax_code="BBB",
            stage_code=5,
            stage_label="adulte",
            common_name="B",
            sandre_code=None,
            scientific_name="B b",
            display_order=2,
            now=now,
        )
    ids = [taxon.id for taxon in repository.list_all()]
    with pytest.raises(ValueError, match="même raccourci"), connection:
        repository.save_configuration(
            ((ids[0], True, 1, "A"), (ids[1], True, 2, "A")),
            now,
        )
    connection.close()
