from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PassageEditValue:
    taxon_id: int
    individual_count: int
    direction: int
    confidence: str
    needs_review: bool
    glass_position: str
    comment: str | None
