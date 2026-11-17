from pathlib import Path

from open_fish_reader.database.connection import (
    open_database,
)
from open_fish_reader.services.taxon_reference_service import (
    TaxonReferenceService,
)


def test_agj_is_yellow_eel_juvenile(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "catalog.sqlite"

    connection = open_database(database_path)

    try:
        # Table minimale nécessaire aux clés
        # étrangères des autres schémas.
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
        row = connection.execute(
            """
            SELECT
                station_taxon.tax_code,
                station_taxon.common_name,
                station_taxon.stage_code,
                development_stages.stage_label,
                station_taxon.scientific_name,
                reference_taxon.source_tax_id
            FROM taxa AS station_taxon
            JOIN taxon_reference
                AS reference_taxon
                ON reference_taxon.id
                    = station_taxon.reference_id
            LEFT JOIN development_stages
                ON development_stages.stage_code
                    = station_taxon.stage_code
            WHERE station_taxon.tax_code = 'AGJ'
            """
        ).fetchone()

        assert row is not None
        assert row["tax_code"] == "AGJ"
        assert row["common_name"] == ("Anguille jaune")
        assert row["stage_code"] == "4"
        assert row["stage_label"] == ("Juvénile")
        assert row["scientific_name"] == ("Anguilla anguilla")
        assert row["source_tax_id"] == 8

    finally:
        connection.close()
