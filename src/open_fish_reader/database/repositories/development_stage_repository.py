from __future__ import annotations

import sqlite3

from ...domain.development_stage import (
    DevelopmentStage,
)


class DevelopmentStageRepository:
    def __init__(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        self.connection = connection

    def list_active(
        self,
    ) -> list[DevelopmentStage]:
        rows = self.connection.execute(
            """
            SELECT
                stage_code,
                stage_label,
                display_order
            FROM development_stages
            WHERE is_active = 1
            ORDER BY
                display_order,
                stage_code
            """
        ).fetchall()

        return [
            DevelopmentStage(
                code=str(row["stage_code"]),
                label=str(row["stage_label"]),
                display_order=int(row["display_order"]),
            )
            for row in rows
        ]
