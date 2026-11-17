from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ..database.connection import open_database
from ..database.taxon_reference_schema import (
    create_taxon_reference_schema,
)
from ..database.taxon_reference_seed import (
    DEVELOPMENT_STAGE_SEED,
    TAXON_REFERENCE_SEED,
)


class TaxonReferenceService:
    """Initialise le référentiel et la copie propre à la station."""

    def initialize(
        self,
        database_path: Path,
    ) -> None:
        connection = open_database(database_path)

        try:
            create_taxon_reference_schema(connection)

            now = datetime.now().astimezone().isoformat(timespec="milliseconds")

            with connection:
                self._seed_development_stages(connection)
                self._seed_taxon_reference(
                    connection,
                    now,
                )
                self._link_existing_station_taxa(connection)
                self._copy_missing_reference_taxa(
                    connection,
                    now,
                )

        finally:
            connection.close()

    @staticmethod
    def _seed_development_stages(
        connection,
    ) -> None:
        connection.executemany(
            """
            INSERT INTO development_stages (
                stage_code,
                stage_label,
                display_order,
                is_active
            )
            VALUES (?, ?, ?, 1)
            ON CONFLICT(stage_code) DO UPDATE SET
                stage_label = excluded.stage_label,
                display_order = excluded.display_order
            """,
            [
                (
                    code,
                    label,
                    order,
                )
                for order, (
                    code,
                    label,
                ) in enumerate(
                    DEVELOPMENT_STAGE_SEED,
                    start=1,
                )
            ],
        )

    @staticmethod
    def _seed_taxon_reference(
        connection,
        now: str,
    ) -> None:
        for order, row in enumerate(
            TAXON_REFERENCE_SEED,
            start=1,
        ):
            (
                source_id,
                code,
                stage,
                common,
                sandre,
                scientific,
            ) = row

            reference_uuid = str(
                uuid5(
                    NAMESPACE_URL,
                    (f"open-fish-reader:reference:{code}"),
                )
            )

            connection.execute(
                """
                INSERT INTO taxon_reference (
                    reference_uuid,
                    source_tax_id,
                    tax_code,
                    stage_code,
                    common_name,
                    sandre_code,
                    scientific_name,
                    display_order,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(tax_code) DO UPDATE SET
                    source_tax_id =
                        excluded.source_tax_id,
                    stage_code =
                        excluded.stage_code,
                    common_name =
                        excluded.common_name,
                    sandre_code =
                        excluded.sandre_code,
                    scientific_name =
                        excluded.scientific_name,
                    display_order =
                        excluded.display_order,
                    updated_at =
                        excluded.updated_at
                """,
                (
                    reference_uuid,
                    source_id,
                    code,
                    stage,
                    common,
                    sandre,
                    scientific,
                    order,
                    now,
                    now,
                ),
            )

    @staticmethod
    def _link_existing_station_taxa(
        connection,
    ) -> None:
        # Rattache les taxons existants au référentiel
        # sans écraser les modifications opérateur.
        connection.execute(
            """
            UPDATE taxa AS station_taxon
            SET reference_id = (
                SELECT reference_taxon.id
                FROM taxon_reference
                    AS reference_taxon
                WHERE reference_taxon.tax_code
                    = station_taxon.tax_code
            )
            WHERE station_taxon.reference_id IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM taxon_reference
                      AS reference_taxon
                  WHERE reference_taxon.tax_code
                      = station_taxon.tax_code
              )
            """
        )

    @staticmethod
    def _copy_missing_reference_taxa(
        connection,
        now: str,
    ) -> None:
        # Copie seulement les taxons de référence
        # absents du catalogue de la station.
        connection.execute(
            """
            INSERT INTO taxa (
                taxon_uuid,
                reference_id,
                tax_code,
                stage_code,
                common_name,
                sandre_code,
                scientific_name,
                is_active,
                keyboard_shortcut,
                display_order,
                source_type,
                is_archived,
                created_at,
                updated_at
            )
            SELECT
                reference_taxon.reference_uuid,
                reference_taxon.id,
                reference_taxon.tax_code,
                reference_taxon.stage_code,
                reference_taxon.common_name,
                reference_taxon.sandre_code,
                reference_taxon.scientific_name,
                0,
                NULL,
                reference_taxon.display_order,
                'reference',
                0,
                ?,
                ?
            FROM taxon_reference
                AS reference_taxon
            WHERE NOT EXISTS (
                SELECT 1
                FROM taxa AS station_taxon
                WHERE station_taxon.reference_id
                    = reference_taxon.id
            )
              AND NOT EXISTS (
                  SELECT 1
                  FROM taxa AS station_taxon
                  WHERE station_taxon.tax_code
                      = reference_taxon.tax_code
              )
            """,
            (
                now,
                now,
            ),
        )
