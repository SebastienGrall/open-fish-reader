from __future__ import annotations

import csv
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from ..database.catalog_schema import create_catalog_schema
from ..database.connection import open_database
from ..database.repositories.taxon_repository import TaxonRepository
from ..domain.taxon import Taxon


class TaxonCatalogService:
    def ensure_seeded(self, database_path: Path) -> None:
        connection = open_database(database_path)
        try:
            create_catalog_schema(connection)
            now = datetime.now().astimezone()
            resource = files("open_fish_reader.resources").joinpath("taxa.csv")
            with resource.open("r", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream, delimiter=";")
                with connection:
                    repository = TaxonRepository(connection)
                    for order, row in enumerate(reader, start=1):
                        repository.upsert_seed(
                            source_tax_id=int(row["tax_id"]),
                            tax_code=row["tax_code"],
                            stage_code=int(row["stage_code"]),
                            stage_label=row["stage_label"],
                            common_name=row["common_name"],
                            sandre_code=row["sandre_code"].strip() or None,
                            scientific_name=row["scientific_name"],
                            display_order=order,
                            now=now,
                        )
        finally:
            connection.close()

    def list_active(self, database_path: Path) -> list[Taxon]:
        connection = open_database(database_path)
        try:
            return TaxonRepository(connection).list_active()
        finally:
            connection.close()
