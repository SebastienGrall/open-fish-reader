from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from ...domain.passage import Passage


class PassageRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(
        self,
        *,
        passage_uuid: UUID,
        station_id: int,
        video_part_id: int,
        taxon_id: int,
        frame_number: int,
        position_ms: int,
        observed_at: datetime,
        individual_count: int,
        direction: int,
        confidence: str,
        needs_review: bool,
        glass_position: str,
        length_mm: int | None,
        comment: str | None,
        now: datetime,
    ) -> int:
        timestamp = now.isoformat(timespec="milliseconds")
        cursor = self.connection.execute(
            """
            INSERT INTO passages (
                passage_uuid, station_id, video_part_id, taxon_id,
                frame_number, position_ms, observed_at, individual_count,
                direction, confidence, needs_review, glass_position,
                length_mm, comment, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(passage_uuid),
                station_id,
                video_part_id,
                taxon_id,
                frame_number,
                position_ms,
                observed_at.isoformat(timespec="milliseconds"),
                individual_count,
                direction,
                confidence,
                int(needs_review),
                glass_position,
                length_mm,
                comment or None,
                timestamp,
                timestamp,
            ),
        )
        return int(cursor.lastrowid)

    def get(self, passage_id: int) -> Passage | None:
        row = self.connection.execute(
            "SELECT * FROM passages WHERE id = ?", (passage_id,)
        ).fetchone()
        return self._from_row(row) if row is not None else None

    def list_for_video_part(self, video_part_id: int) -> list[Passage]:
        rows = self.connection.execute(
            """
            SELECT * FROM passages
            WHERE video_part_id = ?
            ORDER BY observed_at, id
            """,
            (video_part_id,),
        ).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Passage:
        return Passage(
            id=int(row["id"]),
            passage_uuid=str(row["passage_uuid"]),
            station_id=int(row["station_id"]),
            video_part_id=int(row["video_part_id"]),
            taxon_id=int(row["taxon_id"]),
            frame_number=int(row["frame_number"]),
            position_ms=int(row["position_ms"]),
            observed_at=datetime.fromisoformat(row["observed_at"]),
            individual_count=int(row["individual_count"]),
            direction=int(row["direction"]),
            confidence=str(row["confidence"]),
            needs_review=bool(row["needs_review"]),
            glass_position=str(row["glass_position"]),
            length_mm=(int(row["length_mm"]) if row["length_mm"] is not None else None),
            comment=(str(row["comment"]) if row["comment"] is not None else None),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
