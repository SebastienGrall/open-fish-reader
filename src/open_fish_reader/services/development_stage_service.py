from __future__ import annotations

from pathlib import Path

from ..database.connection import open_database
from ..database.repositories.development_stage_repository import (
    DevelopmentStageRepository,
)
from ..domain.development_stage import (
    DevelopmentStage,
)


class DevelopmentStageService:
    def list_active(
        self,
        database_path: Path,
    ) -> list[DevelopmentStage]:
        connection = open_database(database_path)

        try:
            repository = DevelopmentStageRepository(connection)

            return repository.list_active()

        finally:
            connection.close()
