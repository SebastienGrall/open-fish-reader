from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..database.connection import open_database


@dataclass(frozen=True, slots=True)
class DatabaseBackupResult:
    output_path: Path
    integrity_check: str
    foreign_key_error_count: int


class DatabaseBackupService:
    def backup(
        self,
        source_database_path: Path,
        destination_folder: Path,
        station_slug: str,
    ) -> DatabaseBackupResult:
        if not source_database_path.is_file():
            raise ValueError("La base de la station est introuvable.")

        destination_folder.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = self._available_path(
            destination_folder / f"{station_slug}_{timestamp}.sqlite"
        )

        source = open_database(source_database_path)
        destination = sqlite3.connect(output_path)
        try:
            source.backup(destination)
            destination.commit()
            integrity_row = destination.execute("PRAGMA integrity_check").fetchone()
            integrity_check = str(integrity_row[0]) if integrity_row else "unknown"
            foreign_key_errors = destination.execute("PRAGMA foreign_key_check").fetchall()
        except Exception:
            destination.close()
            source.close()
            output_path.unlink(missing_ok=True)
            raise
        else:
            destination.close()
            source.close()

        if integrity_check.lower() != "ok" or foreign_key_errors:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(
                "La sauvegarde a échoué au contrôle d'intégrité "
                f"(integrity_check={integrity_check}, "
                f"foreign_key_errors={len(foreign_key_errors)})."
            )

        return DatabaseBackupResult(
            output_path=output_path,
            integrity_check=integrity_check,
            foreign_key_error_count=len(foreign_key_errors),
        )

    @staticmethod
    def _available_path(path: Path) -> Path:
        if not path.exists():
            return path
        for index in range(1, 10_000):
            candidate = path.with_name(f"{path.stem}_{index:03d}{path.suffix}")
            if not candidate.exists():
                return candidate
        raise OSError("Impossible de trouver un nom disponible pour la sauvegarde.")
