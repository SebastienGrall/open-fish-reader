from __future__ import annotations

from collections import OrderedDict
from threading import RLock

from .frame import DecodedFrame


class PersistentFrameBuffer:
    """Tampon LRU thread-safe, borné par la mémoire des QImage."""

    def __init__(self, maximum_bytes: int) -> None:
        if maximum_bytes <= 0:
            raise ValueError("maximum_bytes doit être strictement positif.")

        self.maximum_bytes = maximum_bytes
        self._frames: OrderedDict[int, DecodedFrame] = OrderedDict()
        self._sizes: dict[int, int] = {}
        self._used_bytes = 0
        self._lock = RLock()

    @property
    def used_bytes(self) -> int:
        with self._lock:
            return self._used_bytes

    @property
    def frame_count(self) -> int:
        with self._lock:
            return len(self._frames)

    def contains(self, frame_index: int) -> bool:
        with self._lock:
            return frame_index in self._frames

    def get(self, frame_index: int) -> DecodedFrame | None:
        with self._lock:
            frame = self._frames.get(frame_index)
            if frame is None:
                return None
            self._frames.move_to_end(frame_index)
            return frame

    def put(self, frame_index: int, frame: DecodedFrame) -> None:
        with self._lock:
            size = self._frame_size(frame)
            if size > self.maximum_bytes:
                return

            if frame_index in self._frames:
                self._used_bytes -= self._sizes[frame_index]
                del self._frames[frame_index]

            self._frames[frame_index] = frame
            self._sizes[frame_index] = size
            self._used_bytes += size
            self._frames.move_to_end(frame_index)
            self._evict_unlocked()

    def protect_range(self, first_index: int, last_index: int) -> None:
        """Rend récent l'historique à conserver avant éviction."""
        with self._lock:
            for frame_index in range(first_index, last_index + 1):
                if frame_index in self._frames:
                    self._frames.move_to_end(frame_index)

    def clear(self) -> None:
        with self._lock:
            self._frames.clear()
            self._sizes.clear()
            self._used_bytes = 0

    def indices(self) -> tuple[int, ...]:
        with self._lock:
            return tuple(sorted(self._frames))

    def _evict_unlocked(self) -> None:
        while self._used_bytes > self.maximum_bytes and self._frames:
            frame_index, _frame = self._frames.popitem(last=False)
            self._used_bytes -= self._sizes.pop(frame_index)

    @staticmethod
    def _frame_size(frame: DecodedFrame) -> int:
        return frame.image.bytesPerLine() * frame.image.height()
