from __future__ import annotations

import sqlite3
from datetime import datetime

from ...domain.taxon import Taxon


class TaxonRepository:
    def __init__(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        self.connection = connection

    def list_all(self) -> list[Taxon]:
        rows = self.connection.execute(
            """
            SELECT
                taxa.*,
                taxon_reference.source_tax_id
                    AS source_tax_id,
                development_stages.stage_label
                    AS stage_label
            FROM taxa
            LEFT JOIN taxon_reference
                ON taxon_reference.id
                    = taxa.reference_id
            LEFT JOIN development_stages
                ON development_stages.stage_code
                    = taxa.stage_code
            WHERE taxa.is_archived = 0
            ORDER BY
                taxa.display_order,
                taxa.tax_code
            """
        ).fetchall()

        return [self._from_row(row) for row in rows]

    def list_active(self) -> list[Taxon]:
        rows = self.connection.execute(
            """
            SELECT
                taxa.*,
                taxon_reference.source_tax_id
                    AS source_tax_id,
                development_stages.stage_label
                    AS stage_label
            FROM taxa
            LEFT JOIN taxon_reference
                ON taxon_reference.id
                    = taxa.reference_id
            LEFT JOIN development_stages
                ON development_stages.stage_code
                    = taxa.stage_code
            WHERE taxa.is_active = 1
              AND taxa.is_archived = 0
            ORDER BY
                taxa.display_order,
                taxa.tax_code
            """
        ).fetchall()

        return [self._from_row(row) for row in rows]

    def save_configuration(
        self,
        configuration: tuple[
            tuple[
                int,
                bool,
                int,
                str | None,
            ],
            ...,
        ],
        now: datetime,
    ) -> None:
        timestamp = now.isoformat(timespec="milliseconds")

        shortcuts = [
            shortcut
            for (
                _taxon_id,
                active,
                _display_order,
                shortcut,
            ) in configuration
            if active and shortcut is not None
        ]

        if len(shortcuts) != len(set(shortcuts)):
            raise ValueError("Deux taxons actifs utilisent le même raccourci.")

        for (
            taxon_id,
            active,
            display_order,
            shortcut,
        ) in configuration:
            self.connection.execute(
                """
                UPDATE taxa
                SET
                    is_active = ?,
                    display_order = ?,
                    keyboard_shortcut = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    int(active),
                    max(0, display_order),
                    shortcut,
                    timestamp,
                    taxon_id,
                ),
            )

    @staticmethod
    def _from_row(
        row: sqlite3.Row,
    ) -> Taxon:
        return Taxon(
            id=int(row["id"]),
            taxon_uuid=str(row["taxon_uuid"]),
            source_tax_id=(int(row["source_tax_id"]) if row["source_tax_id"] is not None else None),
            tax_code=str(row["tax_code"]),
            stage_code=(str(row["stage_code"]) if row["stage_code"] is not None else None),
            stage_label=(str(row["stage_label"]) if row["stage_label"] is not None else None),
            common_name=str(row["common_name"]),
            sandre_code=(str(row["sandre_code"]) if row["sandre_code"] is not None else None),
            scientific_name=str(row["scientific_name"]),
            is_active=bool(row["is_active"]),
            keyboard_shortcut=(
                str(row["keyboard_shortcut"]) if row["keyboard_shortcut"] is not None else None
            ),
            display_order=int(row["display_order"]),
        )
