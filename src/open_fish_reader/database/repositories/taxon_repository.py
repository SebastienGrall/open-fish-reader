from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from ...domain.taxon import Taxon


class TaxonRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert_seed(
        self,
        *,
        source_tax_id: int,
        tax_code: str,
        stage_code: int,
        stage_label: str,
        common_name: str,
        sandre_code: str | None,
        scientific_name: str,
        display_order: int,
        now: datetime,
    ) -> None:
        code = tax_code.strip().upper()
        taxon_uuid = str(uuid5(NAMESPACE_URL, f"open-fish-reader:taxon:{code}"))
        timestamp = now.isoformat(timespec="milliseconds")
        self.connection.execute(
            """
            INSERT INTO taxa (
                taxon_uuid, source_tax_id, tax_code, stage_code, stage_label,
                common_name, sandre_code, scientific_name, is_active,
                keyboard_shortcut, display_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?)
            ON CONFLICT(tax_code) DO UPDATE SET
                source_tax_id = excluded.source_tax_id,
                stage_code = excluded.stage_code,
                stage_label = excluded.stage_label,
                common_name = excluded.common_name,
                sandre_code = excluded.sandre_code,
                scientific_name = excluded.scientific_name,
                updated_at = excluded.updated_at
            """,
            (
                taxon_uuid,
                source_tax_id,
                code,
                stage_code,
                stage_label.strip(),
                common_name.strip(),
                sandre_code or None,
                scientific_name.strip(),
                display_order,
                timestamp,
                timestamp,
            ),
        )

    def list_all(self) -> list[Taxon]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM taxa
            WHERE is_archived = 0
            ORDER BY display_order, tax_code
            """
        ).fetchall()

        return [self._from_row(row) for row in rows]

    def list_active(self) -> list[Taxon]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM taxa
            WHERE is_active = 1
            AND is_archived = 0
            ORDER BY display_order, tax_code
            """
        ).fetchall()

        return [self._from_row(row) for row in rows]

    def save_configuration(
        self,
        configuration: tuple[tuple[int, bool, int, str | None], ...],
        now: datetime,
    ) -> None:
        timestamp = now.isoformat(timespec="milliseconds")
        shortcuts = [
            shortcut
            for _taxon_id, active, _order, shortcut in configuration
            if active and shortcut is not None
        ]
        if len(shortcuts) != len(set(shortcuts)):
            raise ValueError("Deux taxons actifs utilisent le même raccourci.")

        for taxon_id, active, display_order, shortcut in configuration:
            self.connection.execute(
                """
                UPDATE taxa
                SET is_active = ?, display_order = ?, keyboard_shortcut = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (int(active), max(0, display_order), shortcut, timestamp, taxon_id),
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Taxon:
        return Taxon(
            id=int(row["id"]),
            taxon_uuid=str(row["taxon_uuid"]),
            source_tax_id=(int(row["source_tax_id"]) if row["source_tax_id"] is not None else None),
            tax_code=str(row["tax_code"]),
            stage_code=int(row["stage_code"]),
            stage_label=str(row["stage_label"]),
            common_name=str(row["common_name"]),
            sandre_code=(str(row["sandre_code"]) if row["sandre_code"] is not None else None),
            scientific_name=str(row["scientific_name"]),
            is_active=bool(row["is_active"]),
            keyboard_shortcut=(
                str(row["keyboard_shortcut"]) if row["keyboard_shortcut"] is not None else None
            ),
            display_order=int(row["display_order"]),
        )
