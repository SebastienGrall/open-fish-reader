from datetime import UTC, datetime
from pathlib import Path

from open_fish_reader.database.catalog_schema import create_catalog_schema
from open_fish_reader.database.connection import open_database
from open_fish_reader.database.repositories.taxon_repository import TaxonRepository


def test_agj_is_yellow_eel_juvenile(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "catalog.sqlite")
    create_catalog_schema(connection)
    repository = TaxonRepository(connection)
    now = datetime.now(UTC)
    with connection:
        repository.upsert_seed(
            source_tax_id=8,
            tax_code="AGJ",
            stage_code=4,
            stage_label="juvénile",
            common_name="Anguille jaune",
            sandre_code="2038",
            scientific_name="Anguilla anguilla",
            display_order=1,
            now=now,
        )
    taxon = repository.list_all()[0]
    assert taxon.tax_code == "AGJ"
    assert taxon.stage_code == 4
    assert taxon.common_name == "Anguille jaune"
    connection.close()
