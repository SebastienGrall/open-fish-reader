from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Taxon:
    id: int
    taxon_uuid: str
    source_tax_id: int | None
    tax_code: str
    stage_code: int
    stage_label: str
    common_name: str
    sandre_code: str | None
    scientific_name: str
    is_active: bool
    keyboard_shortcut: str | None
    display_order: int
