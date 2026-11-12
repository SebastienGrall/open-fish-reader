from __future__ import annotations

from collections import OrderedDict
from threading import RLock

from .frame import DecodedFrame


class PersistentFrameBuffer:
    """Tampon FIFO thread-safe et borné pour un flux vidéo séquentiel.

    Contrairement à un LRU généraliste, une lecture vidéo doit évincer les
    plus petits indices déjà consommés, jamais les prochaines images à lire.
    """

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
            return self._frames.get(frame_index)

    def can_fit(self, byte_count: int) -> bool:
        with self._lock:
            return self._used_bytes + byte_count <= self.maximum_bytes

    def put(self, frame_index: int, frame: DecodedFrame) -> bool:
        """Ajoute une image sans évincer une image future.

        Le producteur doit d'abord appeler discard_before(). False signifie
        qu'il doit attendre que le consommateur avance.
        """
        with self._lock:
            size = self.frame_size(frame)
            previous_size = self._sizes.get(frame_index, 0)
            projected = self._used_bytes - previous_size + size
            if size > self.maximum_bytes or projected > self.maximum_bytes:
                return False

            if frame_index in self._frames:
                self._used_bytes -= previous_size
                del self._frames[frame_index]
            self._frames[frame_index] = frame
            self._sizes[frame_index] = size
            self._used_bytes += size
            return True

    def discard_before(self, first_index_to_keep: int) -> None:
        with self._lock:
            removable = [index for index in self._frames if index < first_index_to_keep]
            for index in removable:
                del self._frames[index]
                self._used_bytes -= self._sizes.pop(index)

    def clear(self) -> None:
        with self._lock:
            self._frames.clear()
            self._sizes.clear()
            self._used_bytes = 0

    def indices(self) -> tuple[int, ...]:
        with self._lock:
            return tuple(self._frames)

    @staticmethod
    def frame_size(frame: DecodedFrame) -> int:
        return frame.image.bytesPerLine() * frame.image.height()
