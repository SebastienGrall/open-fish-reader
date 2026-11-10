from __future__ import annotations

from dataclasses import dataclass

from ..domain.indexed_video_part import IndexedVideoPart

BYTES_PER_RGB_PIXEL = 3
DEFAULT_FULL_CACHE_LIMIT_BYTES = 128 * 1024 * 1024
DEFAULT_ABSOLUTE_CACHE_LIMIT_BYTES = 256 * 1024 * 1024
DEFAULT_FULL_CACHE_DURATION_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class CacheDecision:
    estimated_bytes: int
    duration_seconds: float
    allow_full_cache: bool
    reason: str


def estimate_decoded_memory_bytes(part: IndexedVideoPart) -> int:
    frame_count = max(0, part.frame_count)
    width = max(0, part.frame_width)
    height = max(0, part.frame_height)
    return width * height * BYTES_PER_RGB_PIXEL * frame_count


def estimate_duration_seconds(part: IndexedVideoPart) -> float:
    if part.recording_fps <= 0:
        return 0.0
    return part.frame_count / part.recording_fps


def decide_full_cache(
    part: IndexedVideoPart,
    full_cache_limit_bytes: int = DEFAULT_FULL_CACHE_LIMIT_BYTES,
    maximum_duration_seconds: float = DEFAULT_FULL_CACHE_DURATION_SECONDS,
) -> CacheDecision:
    estimated_bytes = estimate_decoded_memory_bytes(part)
    duration_seconds = estimate_duration_seconds(part)

    if estimated_bytes > full_cache_limit_bytes:
        return CacheDecision(
            estimated_bytes=estimated_bytes,
            duration_seconds=duration_seconds,
            allow_full_cache=False,
            reason=("mémoire décodée estimée supérieure à la limite du cache complet"),
        )

    if duration_seconds > maximum_duration_seconds:
        return CacheDecision(
            estimated_bytes=estimated_bytes,
            duration_seconds=duration_seconds,
            allow_full_cache=False,
            reason="durée supérieure à la limite du cache complet",
        )

    return CacheDecision(
        estimated_bytes=estimated_bytes,
        duration_seconds=duration_seconds,
        allow_full_cache=True,
        reason="fichier compatible avec le cache complet",
    )


def format_megabytes(byte_count: int) -> str:
    return f"{byte_count / (1024 * 1024):.1f} Mo"
