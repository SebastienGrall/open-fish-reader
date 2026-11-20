from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DatabaseInformation:
    database_path: Path
    schema_version: int
    created_with_app_version: str
    last_opened_with_app_version: str
    created_at: str
    updated_at: str
