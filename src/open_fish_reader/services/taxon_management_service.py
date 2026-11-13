from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..database.connection import open_database
from ..database.repositories.taxon_management_repository import TaxonManagementRepository
from ..domain.taxon import Taxon
from ..ui.dialogs.taxon_editor_dialog import TaxonEditorValue


class TaxonManagementService:
    def create(self, database_path: Path, value: TaxonEditorValue) -> int:
        connection = open_database(database_path)
        try:
            with connection:
                return TaxonManagementRepository(connection).create_custom(
                    tax_code=value.tax_code,
                    common_name=value.common_name,
                    scientific_name=value.scientific_name,
                    sandre_code=value.sandre_code,
                    stage_code=value.stage_code,
                    stage_label=value.stage_label,
                    is_active=value.is_active,
                    display_order=value.display_order,
                    keyboard_shortcut=value.keyboard_shortcut,
                    now=datetime.now().astimezone(),
                )
        finally:
            connection.close()

    def update(self, database_path: Path, taxon_id: int, value: TaxonEditorValue) -> None:
        connection = open_database(database_path)
        try:
            with connection:
                TaxonManagementRepository(connection).update(
                    taxon_id=taxon_id,
                    common_name=value.common_name,
                    scientific_name=value.scientific_name,
                    sandre_code=value.sandre_code,
                    stage_code=value.stage_code,
                    stage_label=value.stage_label,
                    is_active=value.is_active,
                    display_order=value.display_order,
                    keyboard_shortcut=value.keyboard_shortcut,
                    now=datetime.now().astimezone(),
                )
        finally:
            connection.close()

    def archive(self, database_path: Path, taxon_id: int) -> None:
        connection = open_database(database_path)
        try:
            with connection:
                TaxonManagementRepository(connection).archive(taxon_id, datetime.now().astimezone())
        finally:
            connection.close()

    def get(self, database_path: Path, taxon_id: int) -> Taxon | None:
        connection = open_database(database_path)
        try:
            return TaxonManagementRepository(connection).get(taxon_id)
        finally:
            connection.close()
