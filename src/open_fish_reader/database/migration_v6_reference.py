from __future__ import annotations

import sqlite3

from .taxon_reference_schema import (
    create_taxon_reference_schema,
)
from .taxon_reference_seed import (
    DEVELOPMENT_STAGE_SEED,
)


def migrate_taxa_to_reference_v6(
    connection: sqlite3.Connection,
) -> None:
    """Migre le catalogue taxonomique vers le schéma v6.

    La migration :
    - crée le référentiel des stades ;
    - crée le référentiel taxonomique protégé ;
    - rend le stade facultatif ;
    - limite le code taxon à 10 caractères ;
    - conserve la configuration propre à la station.
    """

    too_long = connection.execute(
        """
        SELECT tax_code
        FROM taxa
        WHERE length(tax_code) > 10
        LIMIT 1
        """
    ).fetchone()

    if too_long is not None:
        raise RuntimeError(
            f"Migration impossible : le code taxon {too_long['tax_code']!r} dépasse 10 caractères."
        )

    old_columns = {row["name"] for row in connection.execute("PRAGMA table_info(taxa)").fetchall()}

    # Crée development_stages et
    # taxon_reference. La table taxa existe
    # déjà, donc son CREATE TABLE IF NOT EXISTS
    # ne la remplace pas.
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
        ON CONFLICT(stage_code) DO UPDATE SET
            stage_label = excluded.stage_label,
            display_order = excluded.display_order
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

    # La présence de stage_label indique
    # l'ancien schéma v5 à reconstruire.
    if "stage_label" in old_columns:
        connection.execute("DROP TABLE IF EXISTS taxa_v6")
        connection.executescript(
            """
            CREATE TABLE taxa_v6 (
                id INTEGER PRIMARY KEY,
                taxon_uuid TEXT NOT NULL UNIQUE,

                reference_id INTEGER
                    REFERENCES taxon_reference(id)
                    ON DELETE RESTRICT,

                tax_code TEXT NOT NULL UNIQUE
                    CHECK (
                        length(tax_code)
                        BETWEEN 1 AND 10
                    ),

                stage_code TEXT
                    REFERENCES development_stages(
                        stage_code
                    )
                    ON DELETE RESTRICT,

                common_name TEXT NOT NULL,
                sandre_code TEXT,
                scientific_name TEXT NOT NULL,

                is_active INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (
                        is_active IN (0, 1)
                    ),

                keyboard_shortcut TEXT UNIQUE,

                display_order INTEGER NOT NULL
                    DEFAULT 0,

                source_type TEXT NOT NULL
                    DEFAULT 'reference'
                    CHECK (
                        source_type IN (
                            'reference',
                            'custom',
                            'csv'
                        )
                    ),

                is_archived INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (
                        is_archived IN (0, 1)
                    ),

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        if "source_type" in old_columns:
            source_type_expression = """
                CASE source_type
                    WHEN 'catalog' THEN 'reference'
                    WHEN 'reference' THEN 'reference'
                    WHEN 'custom' THEN 'custom'
                    WHEN 'csv' THEN 'csv'
                    ELSE 'reference'
                END
            """
        else:
            source_type_expression = "'reference'"

        is_archived_expression = "is_archived" if "is_archived" in old_columns else "0"

        unknown_stage = connection.execute(
            """
            SELECT DISTINCT
                CAST(stage_code AS TEXT)
                    AS stage_code
            FROM taxa
            WHERE stage_code IS NOT NULL
            AND CAST(stage_code AS TEXT)
                NOT IN ('', '0')
            AND CAST(stage_code AS TEXT)
                NOT IN (
                    SELECT stage_code
                    FROM development_stages
                )
            LIMIT 1
            """
        ).fetchone()

        if unknown_stage is not None:
            raise RuntimeError(
                "Migration impossible : le stade "
                f"{unknown_stage['stage_code']!r} "
                "n'existe pas dans le référentiel."
            )

        connection.execute(
            f"""
            INSERT INTO taxa_v6 (
                id,
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
                id,
                taxon_uuid,
                NULL,
                tax_code,
                CASE
                    WHEN stage_code IS NULL
                    THEN NULL

                    WHEN TRIM(
                        CAST(stage_code AS TEXT)
                    ) IN ('', '0')
                    THEN NULL

                    ELSE TRIM(
                        CAST(stage_code AS TEXT)
                    )
                END,
                common_name,
                sandre_code,
                scientific_name,
                is_active,
                keyboard_shortcut,
                display_order,
                {source_type_expression},
                {is_archived_expression},
                created_at,
                updated_at
            FROM taxa
            """
        )

        old_count = connection.execute("SELECT COUNT(*) FROM taxa").fetchone()[0]

        new_count = connection.execute("SELECT COUNT(*) FROM taxa_v6").fetchone()[0]

        if new_count != old_count:
            raise RuntimeError(
                "Migration taxonomique incomplète : "
                f"{old_count} taxons avant migration, "
                f"{new_count} après copie."
            )

        connection.executescript(
            """
            DROP TABLE taxa;

            ALTER TABLE taxa_v6
                RENAME TO taxa;

            CREATE INDEX
                idx_taxa_active_order
            ON taxa (
                is_active,
                is_archived,
                display_order,
                tax_code
            );
            """
        )

    else:
        # Une ancienne table peut déjà avoir
        # perdu stage_label tout en n'ayant pas
        # encore reference_id.
        current_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(taxa)").fetchall()
        }

        if "reference_id" not in current_columns:
            connection.execute(
                """
                ALTER TABLE taxa
                ADD COLUMN reference_id INTEGER
                    REFERENCES taxon_reference(id)
            """
            )
