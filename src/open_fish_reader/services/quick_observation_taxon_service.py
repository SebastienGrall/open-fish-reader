from __future__ import annotations

from pathlib import Path

from ..database.connection import open_database
from ..database.repositories.taxon_repository import TaxonRepository
from ..domain.taxon import Taxon


class QuickObservationTaxonService:
    def list_active(self, database_path: Path) -> list[Taxon]:
        connection = open_database(database_path)
        try:
            return TaxonRepository(connection).list_active()
        finally:
            connection.close()
