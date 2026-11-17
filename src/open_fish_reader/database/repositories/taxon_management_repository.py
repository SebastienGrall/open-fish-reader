from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import uuid4

from ...domain.taxon import Taxon


class TaxonManagementRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_custom(
        self,
        *,
        tax_code: str,
        common_name: str,
        scientific_name: str,
        sandre_code: str | None,
        stage_code: str | None,
        is_active: bool,
        display_order: int,
        keyboard_shortcut: str | None,
        now: datetime,
    ) -> int:
        code = tax_code.strip().upper()
        timestamp = now.isoformat(timespec="milliseconds")

        archived = self.connection.execute(
            "SELECT id FROM taxa WHERE tax_code = ? AND is_archived = 1",
            (code,),
        ).fetchone()

        try:
            if archived is not None:
                taxon_id = int(archived["id"])
                self.connection.execute(
                    """
                    UPDATE taxa
                    SET stage_code = ?, common_name = ?, sandre_code = ?,
                        scientific_name = ?, is_active = ?,
                        keyboard_shortcut = ?, display_order = ?,
                        source_type = 'custom', is_archived = 0, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        stage_code,
                        common_name,
                        sandre_code,
                        scientific_name,
                        int(is_active),
                        keyboard_shortcut,
                        max(0, display_order),
                        timestamp,
                        taxon_id,
                    ),
                )
                return taxon_id

            cursor = self.connection.execute(
                """
                INSERT INTO taxa (
                    taxon_uuid, reference_id, tax_code, stage_code,
                    common_name, sandre_code, scientific_name, is_active,
                    keyboard_shortcut, display_order, source_type,
                    is_archived, created_at, updated_at
                ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, 'custom', 0, ?, ?)
                """,
                (
                    str(uuid4()),
                    code,
                    stage_code,
                    common_name,
                    sandre_code,
                    scientific_name,
                    int(is_active),
                    keyboard_shortcut,
                    max(0, display_order),
                    timestamp,
                    timestamp,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                f"Le code {code} ou le raccourci {keyboard_shortcut!r} existe déjà."
            ) from error

        return int(cursor.lastrowid)

    def update(
        self,
        *,
        taxon_id: int,
        common_name: str,
        scientific_name: str,
        sandre_code: str | None,
        stage_code: str | None,
        is_active: bool,
        display_order: int,
        keyboard_shortcut: str | None,
        now: datetime,
    ) -> None:
        try:
            self.connection.execute(
                """
                UPDATE taxa
                SET common_name = ?, scientific_name = ?, sandre_code = ?,
                    stage_code = ?, is_active = ?, display_order = ?,
                    keyboard_shortcut = ?, updated_at = ?
                WHERE id = ? AND is_archived = 0
                """,
                (
                    common_name,
                    scientific_name,
                    sandre_code,
                    stage_code,
                    int(is_active),
                    max(0, display_order),
                    keyboard_shortcut,
                    now.isoformat(timespec="milliseconds"),
                    taxon_id,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError(f"Le raccourci {keyboard_shortcut!r} est déjà utilisé.") from error

    def archive(self, taxon_id: int, now: datetime) -> None:
        self.connection.execute(
            """
            UPDATE taxa
            SET is_archived = 1, is_active = 0, keyboard_shortcut = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (now.isoformat(timespec="milliseconds"), taxon_id),
        )

    def get(self, taxon_id: int) -> Taxon | None:
        row = self.connection.execute(
            """
            SELECT taxa.*, taxon_reference.source_tax_id AS source_tax_id,
                   development_stages.stage_label AS stage_label
            FROM taxa
            LEFT JOIN taxon_reference ON taxon_reference.id = taxa.reference_id
            LEFT JOIN development_stages
                ON development_stages.stage_code = taxa.stage_code
            WHERE taxa.id = ?
            """,
            (taxon_id,),
        ).fetchone()
        if row is None:
            return None
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
