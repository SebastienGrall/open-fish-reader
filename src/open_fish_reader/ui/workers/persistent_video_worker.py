from __future__ import annotations

from datetime import timedelta
from fractions import Fraction
from pathlib import Path
from threading import Event, RLock

import av
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from ...domain.indexed_video_part import IndexedVideoPart
from ...video.frame import DecodedFrame
from ...video.persistent_frame_buffer import PersistentFrameBuffer

DEFAULT_BUFFER_BYTES = 256 * 1024 * 1024
DEFAULT_HISTORY_SECONDS = 0.5
DEFAULT_TARGET_AHEAD_SECONDS = 5.0


class PersistentVideoWorker(QObject):
    """Décode un fichier long séquentiellement en le gardant ouvert.

    PlaybackController reste l'unique horloge. Le worker remplit le tampon en
    avance mais n'émet que l'image exactement demandée.
    """

    opened = Signal(int, float)
    frame_ready = Signal(int, object)
    buffer_changed = Signal(int, int, int)
    seek_completed = Signal(int)
    failed = Signal(str)
    stopped = Signal()
    finished = Signal()

    def __init__(
        self,
        part: IndexedVideoPart,
        maximum_buffer_bytes: int = DEFAULT_BUFFER_BYTES,
        history_seconds: float = DEFAULT_HISTORY_SECONDS,
        target_ahead_seconds: float = DEFAULT_TARGET_AHEAD_SECONDS,
    ) -> None:
        super().__init__()
        self.part = part
        self.buffer = PersistentFrameBuffer(maximum_buffer_bytes)
        self._effective_fps_value = self._calculate_effective_fps()
        bytes_per_frame = part.frame_width * part.frame_height * 3

        maximum_buffered_frames = max(
            2,
            maximum_buffer_bytes // bytes_per_frame,
        )

        self.history_frames = min(
            max(1, round(self._effective_fps_value * 0.5)),
            max(1, maximum_buffered_frames // 4),
        )
        self.target_ahead_seconds = max(1.0, target_ahead_seconds)

        self._stop_event = Event()
        self._wake_event = Event()
        self._state_lock = RLock()
        self._requested_index = 0
        self._displayed_index = 0
        self._seek_index: int | None = None
        self._playing = False
        self._playback_speed = 1.0

        self._container: av.container.InputContainer | None = None
        self._stream: av.video.stream.VideoStream | None = None
        self._decoder = None
        self._next_sequential_index = 0
        self._end_of_stream = False

    @Slot()
    def run(self) -> None:
        try:
            print("[Worker] Début ouverture vidéo")
            self._open_file()
            print("[Worker] Fichier ouvert")

            self.opened.emit(
                self.part.frame_count,
                self._effective_fps_value,
            )

            print("[Worker] Attente / décodage des images")

            while not self._stop_event.is_set():
                seek_index = self._consume_seek_request()
                if seek_index is not None:
                    self._seek_and_rebuild(seek_index)
                    continue

                requested_index, displayed_index = self._snapshot_state()
                target_ahead = self._target_ahead_frame_count()
                desired_highest = min(
                    self.part.frame_count - 1,
                    max(requested_index, displayed_index) + target_ahead,
                )
                highest = self._highest_buffered_index()

                if not self._end_of_stream and (highest is None or highest < desired_highest):
                    if self._decode_one():
                        continue
                    self._end_of_stream = True

                self._protect_history(displayed_index)
                self._emit_buffer_state()
                self._wake_event.wait(0.02)
                self._wake_event.clear()

        except (av.error.FFmpegError, OSError, IndexError, RuntimeError) as error:
            self.failed.emit(str(error))
        finally:
            self._close_file()
            self.stopped.emit()
            self.finished.emit()

    @Slot(int)
    def request_frame(self, frame_index: int) -> None:
        with self._state_lock:
            self._requested_index = frame_index
            playing = self._playing

        cached = self.buffer.get(frame_index)

        if cached is not None:
            self.frame_ready.emit(frame_index, cached)
            self._wake_event.set()
            return

        highest = self._highest_buffered_index()

        # En lecture, laisser le décodage séquentiel avancer
        # si l'image demandée se trouve après le buffer.
        if playing and (highest is None or frame_index > highest):
            self._wake_event.set()
            return

        # À l'arrêt, toute image absente doit provoquer
        # un repositionnement du décodeur, même si son index
        # se trouve entre les limites du buffer.
        if not playing:
            with self._state_lock:
                self._seek_index = frame_index

        self._wake_event.set()

    @Slot(int)
    def set_displayed_index(self, frame_index: int) -> None:
        with self._state_lock:
            self._displayed_index = max(0, frame_index)
        self._wake_event.set()

    @Slot(bool)
    def set_playing(self, playing: bool) -> None:
        with self._state_lock:
            self._playing = playing
        self._wake_event.set()

    @Slot(float)
    def set_playback_speed(self, speed: float) -> None:
        with self._state_lock:
            self._playback_speed = max(0.5, min(10.0, speed))
        self._wake_event.set()

    @Slot()
    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()

    def _open_file(self) -> None:
        path = Path(self.part.video_path)
        if not path.is_file():
            raise RuntimeError(f"Vidéo introuvable : {path}")

        self._container = av.open(str(path))
        if not self._container.streams.video:
            raise RuntimeError(f"Aucun flux vidéo dans {path.name}.")

        self._stream = self._container.streams.video[0]
        self._decoder = self._container.decode(self._stream)
        self._next_sequential_index = 0
        self._end_of_stream = False

    def _close_file(self) -> None:
        if self._container is not None:
            self._container.close()
        self._container = None
        self._stream = None
        self._decoder = None

    def _decode_one(self, emit_requested: bool = True) -> bool:
        if self._decoder is None or self._stream is None:
            return False

        try:
            print(f"[Worker] Décodage image {self._next_sequential_index}")
            frame = next(self._decoder)
        except StopIteration:
            return False

        if self._next_sequential_index >= self.part.frame_count:
            return False

        # Les indices scientifiques sont strictement séquentiels. Les PTS ne
        # servent qu'à calculer la position temporelle et l'horodatage.
        frame_index = self._next_sequential_index
        self._next_sequential_index += 1

        decoded = self._convert_frame(frame, frame_index)
        self.buffer.put(frame_index, decoded)

        requested_index, _displayed_index = self._snapshot_state()
        if emit_requested and frame_index == requested_index:
            self.frame_ready.emit(frame_index, decoded)

        self._emit_buffer_state()
        return True

    def _seek_and_rebuild(self, frame_index: int) -> None:
        if self._container is None or self._stream is None:
            return

        time_base = self._stream.time_base
        stream_start = self._stream.start_time or 0
        if time_base is None:
            raise RuntimeError("time_base vidéo indisponible.")

        seek_start_index = max(0, frame_index - self.history_frames)
        target_seconds = seek_start_index / self._effective_fps_value
        relative_pts = round(target_seconds / float(time_base))
        target_pts = max(0, stream_start + relative_pts)

        self._container.seek(
            target_pts,
            stream=self._stream,
            backward=True,
            any_frame=False,
        )
        self._decoder = self._container.decode(self._stream)
        self.buffer.clear()
        self._next_sequential_index = seek_start_index
        self._end_of_stream = False

        while not self._stop_event.is_set():
            if not self._decode_one(emit_requested=False):
                break

            cached = self.buffer.get(frame_index)
            if cached is None:
                continue

            self.frame_ready.emit(frame_index, cached)
            self.seek_completed.emit(frame_index)
            break

    def _convert_frame(
        self,
        frame: av.VideoFrame,
        frame_index: int,
    ) -> DecodedFrame:
        array = frame.to_ndarray(format="rgb24")
        height, width, _channels = array.shape
        image = QImage(
            array.data,
            width,
            height,
            array.strides[0],
            QImage.Format.Format_RGB888,
        ).copy()

        if self._stream is not None:
            time_base: Fraction | None = frame.time_base or self._stream.time_base
            stream_start = self._stream.start_time or 0
        else:
            time_base = None
            stream_start = 0

        if frame.pts is not None and time_base is not None:
            position_ms = max(
                0,
                round(float((frame.pts - stream_start) * time_base) * 1000),
            )
        else:
            position_ms = round(frame_index / self._effective_fps_value * 1000)

        return DecodedFrame(
            image=image,
            frame_number=frame_index,
            pts=frame.pts,
            position_ms=position_ms,
            absolute_timestamp=(self.part.video_start_time + timedelta(milliseconds=position_ms)),
        )

    def _calculate_effective_fps(self) -> float:
        duration_seconds = (self.part.video_end_time - self.part.video_start_time).total_seconds()
        if duration_seconds > 0 and self.part.frame_count > 1:
            return self.part.frame_count / duration_seconds
        if self.part.recording_fps > 0:
            return self.part.recording_fps
        return 20.0

    def _target_ahead_frame_count(self) -> int:
        with self._state_lock:
            playing = self._playing
            speed = self._playback_speed

        target_seconds = (
            3.0
            if not playing
            else min(
                8.0,
                self.target_ahead_seconds + speed,
            )
        )
        requested_frames = round(self._effective_fps_value * target_seconds * max(1.0, speed))

        bytes_per_frame = self.part.frame_width * self.part.frame_height * 3
        if bytes_per_frame <= 0:
            return max(1, requested_frames)

        maximum_buffered_frames = max(
            2,
            self.buffer.maximum_bytes // bytes_per_frame,
        )
        maximum_ahead_frames = max(
            1,
            maximum_buffered_frames - self.history_frames - 4,
        )
        return min(requested_frames, maximum_ahead_frames)

    def _protect_history(self, displayed_index: int) -> None:
        self.buffer.protect_range(
            max(0, displayed_index - self.history_frames),
            displayed_index,
        )

    def _consume_seek_request(self) -> int | None:
        with self._state_lock:
            seek_index = self._seek_index
            self._seek_index = None
            return seek_index

    def _snapshot_state(self) -> tuple[int, int]:
        with self._state_lock:
            return self._requested_index, self._displayed_index

    def _lowest_buffered_index(self) -> int | None:
        indices = self.buffer.indices()
        return indices[0] if indices else None

    def _highest_buffered_index(self) -> int | None:
        indices = self.buffer.indices()
        return indices[-1] if indices else None

    def _emit_buffer_state(self) -> None:
        indices = self.buffer.indices()
        if indices:
            self.buffer_changed.emit(
                indices[0],
                indices[-1],
                self.buffer.used_bytes,
            )
