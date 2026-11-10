from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Station:
    name: str
    source_folder: Path
    slug: str
    id: int | None = None
    extraction_folder: Path | None = None
