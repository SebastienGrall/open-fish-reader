from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..database.connection import open_database
from ..database.repositories.passage_query_repository import PassageQueryRepository


class PassageQueryService:
    def list_for_period(
        self,
        database_path: Path,
        station_id: int,
        start_at: datetime,
        end_at: datetime,
    ) -> list[dict[str, object]]:
        connection = open_database(database_path)
        try:
            return PassageQueryRepository(connection).list_for_period(station_id, start_at, end_at)
        finally:
            connection.close()

    def delete(self, database_path: Path, passage_id: int) -> int | None:
        connection = open_database(database_path)
        try:
            with connection:
                return PassageQueryRepository(connection).delete(passage_id)
        finally:
            connection.close()

    def delete_many(
        self,
        database_path: Path,
        passage_ids: list[int],
    ) -> list[int]:
        if not passage_ids:
            return []

        connection = open_database(database_path)

        try:
            with connection:
                return PassageQueryRepository(connection).delete_many(passage_ids)

        finally:
            connection.close()
