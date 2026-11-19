from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..database.connection import open_database
from ..database.repositories.passage_edit_repository import PassageEditRepository
from ..database.repositories.taxon_repository import TaxonRepository
from ..domain.passage_edit import PassageEditValue
from ..domain.taxon import Taxon


class PassageEditService:
    def get_for_edit(self, database_path: Path, passage_id: int) -> dict[str, object]:
        connection = open_database(database_path)
        try:
            row = PassageEditRepository(connection).get_for_edit(passage_id)
            if row is None:
                raise ValueError("Le passage à modifier est introuvable.")
            return dict(row)
        finally:
            connection.close()

    def list_taxa(self, database_path: Path) -> list[Taxon]:
        connection = open_database(database_path)
        try:
            return TaxonRepository(connection).list_all()
        finally:
            connection.close()

    def update(
        self,
        database_path: Path,
        passage_id: int,
        value: PassageEditValue,
        *,
        measurement_method: str,
        original_glass_position: str,
    ) -> None:
        self._validate(value, measurement_method, original_glass_position)
        connection = open_database(database_path)
        try:
            with connection:
                PassageEditRepository(connection).update(
                    passage_id=passage_id,
                    taxon_id=value.taxon_id,
                    individual_count=value.individual_count,
                    direction=value.direction,
                    confidence=value.confidence,
                    needs_review=value.needs_review,
                    glass_position=value.glass_position,
                    comment=value.comment,
                    now=datetime.now().astimezone(),
                )
        finally:
            connection.close()

    @staticmethod
    def _validate(
        value: PassageEditValue,
        measurement_method: str,
        original_glass_position: str,
    ) -> None:
        if value.individual_count not in range(1, 100):
            raise ValueError("Le nombre d'individus doit être compris entre 1 et 99.")
        if value.direction not in (-1, 0, 1):
            raise ValueError("Le sens est invalide.")
        if value.confidence not in {"certain", "probable", "uncertain"}:
            raise ValueError("La confiance est invalide.")
        if value.glass_position not in {"near", "middle", "far"}:
            raise ValueError("La position vitre est invalide.")
        if (
            measurement_method == "polyline_calibration"
            and value.glass_position != original_glass_position
        ):
            raise ValueError(
                "La position vitre d'un passage mesuré ne peut pas être modifiée. "
                "Supprimez puis recréez le passage pour refaire la mesure."
            )
