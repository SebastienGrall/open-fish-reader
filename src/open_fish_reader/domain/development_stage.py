from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DevelopmentStage:
    code: str
    label: str
    display_order: int
