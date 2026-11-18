from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ..database.connection import open_database
from ..database.repositories.passage_repository import PassageRepository
from ..domain.passage import Passage


@dataclass(frozen=True, slots=True)
class PassageInput:
    station_id: int
    video_part_id: int
    taxon_id: int
    frame_number: int
    position_ms: int
    observed_at: datetime
    individual_count: int
    direction: int
    confidence: str
    needs_review: bool
    glass_position: str
    length_mm: int | None
    comment: str


class PassageService:
    def create(self, database_path: Path, value: PassageInput) -> Passage:
        self._validate(value)
        connection = open_database(database_path)
        try:
            now = datetime.now().astimezone()
            with connection:
                repository = PassageRepository(connection)
                passage_id = repository.create(
                    passage_uuid=uuid4(),
                    station_id=value.station_id,
                    video_part_id=value.video_part_id,
                    taxon_id=value.taxon_id,
                    frame_number=value.frame_number,
                    position_ms=value.position_ms,
                    observed_at=value.observed_at,
                    individual_count=value.individual_count,
                    direction=value.direction,
                    confidence=value.confidence,
                    needs_review=value.needs_review,
                    glass_position=value.glass_position,
                    length_mm=value.length_mm,
                    comment=value.comment,
                    now=now,
                )
                connection.execute(
                    """
                    UPDATE video_parts
                    SET observation_count = observation_count + 1,
                        review_status = 'observed'
                    WHERE id = ?
                    """,
                    (value.video_part_id,),
                )
                passage = repository.get(passage_id)
                if passage is None:
                    raise RuntimeError("Le passage créé est introuvable.")
                return passage
        finally:
            connection.close()

    @staticmethod
    def _validate(value: PassageInput) -> None:
        if not 1 <= value.individual_count <= 99:
            raise ValueError("Le nombre d'individus doit être compris entre 1 et 99.")
        if value.direction not in (-1, 0, 1):
            raise ValueError("Le sens doit valoir -1, 0 ou 1.")
        if value.confidence not in {"certain", "probable", "uncertain"}:
            raise ValueError("Niveau de confiance inconnu.")
        if value.glass_position not in {"near", "middle", "far"}:
            raise ValueError("Position vitre inconnue.")
        if value.frame_number < 0 or value.position_ms < 0:
            raise ValueError("La position vidéo est invalide.")
        if value.length_mm is not None and value.length_mm <= 0:
            raise ValueError("La taille doit être positive ou absente.")
