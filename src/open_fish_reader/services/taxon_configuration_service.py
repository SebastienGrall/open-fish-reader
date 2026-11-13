from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..database.connection import open_database
from ..database.repositories.taxon_repository import TaxonRepository
from ..domain.taxon import Taxon
from ..ui.models.taxon_table_model import EditableTaxon, normalize_shortcut


class TaxonConfigurationService:
    def list_all(self, database_path: Path) -> list[Taxon]:
        connection = open_database(database_path)
        try:
            return TaxonRepository(connection).list_all()
        finally:
            connection.close()

    def save_configuration(
        self,
        database_path: Path,
        taxa: tuple[EditableTaxon, ...],
    ) -> None:
        normalized = tuple(
            (
                taxon.id,
                taxon.is_active,
                taxon.display_order,
                normalize_shortcut(taxon.keyboard_shortcut or ""),
            )
            for taxon in taxa
        )
        active_shortcuts = [
            shortcut
            for _taxon_id, active, _order, shortcut in normalized
            if active and shortcut is not None
        ]
        invalid = [
            shortcut
            for shortcut in active_shortcuts
            if len(shortcut) != 1 or not shortcut.isalnum()
        ]
        if invalid:
            raise ValueError(
                "Les raccourcis doivent contenir une seule lettre ou un seul chiffre : "
                + ", ".join(sorted(set(invalid)))
            )

        connection = open_database(database_path)
        try:
            now = datetime.now().astimezone()
            with connection:
                TaxonRepository(connection).save_configuration(normalized, now)
        finally:
            connection.close()
