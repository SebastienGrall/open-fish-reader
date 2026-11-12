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
DEFAULT_HISTORY_SECONDS = 2.0
DEFAULT_TARGET_AHEAD_SECONDS = 5.0


class PersistentVideoWorker(QObject):
    """Producteur vidéo persistant pour les fichiers longs.

    PlaybackController est l'unique horloge. Ce worker conserve PyAV ouvert,
    remplit un tampon FIFO borné et ne répond qu'aux indices demandés.
    """

    opened = Signal(int, float)
    frame_ready = Signal(int, object)
    buffer_changed = Signal(int, int, int)
    stream_ended = Signal(int)
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
        self.history_frames = max(1, round(self._effective_fps_value * history_seconds))
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
        self._total_frame_count = max(1, part.frame_count)
        self._end_of_stream = False
        self._end_signal_emitted = False

    @Slot()
    def run(self) -> None:
        try:
            self._open_file()
            self.opened.emit(self._total_frame_count, self._effective_fps_value)

            while not self._stop_event.is_set():
                seek_index = self._consume_seek_request()
                if seek_index is not None:
                    self._seek_and_rebuild(seek_index)
                    continue

                requested_index, displayed_index = self._snapshot_state()
                self.buffer.discard_before(max(0, displayed_index - self.history_frames))

                desired_highest = min(
                    self._total_frame_count - 1,
                    max(requested_index, displayed_index) + self._target_ahead_frame_count(),
                )

                if not self._end_of_stream and self._next_sequential_index <= desired_highest:
                    if self._has_capacity_for_next_frame():
                        if self._decode_one():
                            continue
                        self._mark_end_of_stream()
                    else:
                        # Le tampon est plein et l'historique est encore utile.
                        # Attendre que l'affichage avance au lieu d'évincer le futur.
                        self._wake_event.wait(0.01)
                        self._wake_event.clear()
                        continue

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
        if frame_index < 0:
            return
        frame_index = min(frame_index, self._total_frame_count - 1)

        with self._state_lock:
            self._requested_index = frame_index
            playing = self._playing

        cached = self.buffer.get(frame_index)
        if cached is not None:
            self.frame_ready.emit(frame_index, cached)
            self._wake_event.set()
            return

        lowest = self._lowest_buffered_index()
        highest = self._highest_buffered_index()

        # En lecture continue, le producteur atteindra naturellement l'image.
        # Aucun seek avant ne doit vider le tampon.
        if playing and (highest is None or frame_index > highest):
            self._wake_event.set()
            return

        outside_buffer = (
            lowest is None or highest is None or frame_index < lowest or frame_index > highest + 1
        )
        if outside_buffer and not playing:
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
        stream_frames = int(self._stream.frames or 0)
        if stream_frames > 0:
            self._total_frame_count = stream_frames
        self._effective_fps_value = self._calculate_effective_fps(self._total_frame_count)
        self.history_frames = max(1, round(self._effective_fps_value * 2.0))
        self._decoder = self._container.decode(self._stream)
        self._next_sequential_index = 0
        self._end_of_stream = False
        self._end_signal_emitted = False

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
            frame = next(self._decoder)
        except StopIteration:
            return False

        frame_index = self._next_sequential_index
        self._next_sequential_index += 1
        decoded = self._convert_frame(frame, frame_index)

        if not self.buffer.put(frame_index, decoded):
            # Ne jamais perdre l'indice décodé. Revenir d'un cran afin de
            # redécoder après libération du tampon.
            self._next_sequential_index -= 1
            raise RuntimeError("Tampon vidéo saturé avant libération de l'historique.")

        requested_index, _displayed_index = self._snapshot_state()
        if emit_requested and frame_index == requested_index:
            self.frame_ready.emit(frame_index, decoded)

        self._emit_buffer_state()
        return True

    def _seek_and_rebuild(
        self,
        frame_index: int,
    ) -> None:
        if self._container is None or self._stream is None:
            return

        time_base = self._stream.time_base
        stream_start = self._stream.start_time or 0

        if time_base is None:
            raise RuntimeError("time_base vidéo indisponible.")

        seek_start_index = max(
            0,
            frame_index - self.history_frames,
        )

        target_seconds = seek_start_index / self._effective_fps_value

        target_pts = max(
            0,
            stream_start + round(target_seconds / float(time_base)),
        )

        self._container.seek(
            target_pts,
            stream=self._stream,
            backward=True,
            any_frame=False,
        )

        self._decoder = self._container.decode(self._stream)
        self.buffer.clear()
        self._end_of_stream = False
        self._end_signal_emitted = False

        first_frame = True
        next_index = seek_start_index

        while not self._stop_event.is_set():
            try:
                source_frame = next(self._decoder)
            except StopIteration:
                self._mark_end_of_stream()
                break

            if first_frame:
                first_frame = False

                estimated_index = self._index_from_pts(source_frame)

                if estimated_index is not None:
                    # Un seek backward doit commencer
                    # avant l'image demandée.
                    next_index = min(
                        frame_index,
                        estimated_index,
                    )

            decoded_index = next_index
            next_index += 1

            decoded = self._convert_frame(
                source_frame,
                decoded_index,
            )

            if not self.buffer.put(
                decoded_index,
                decoded,
            ):
                # L'historique reconstruit ne doit pas
                # remplir tout le tampon.
                self.buffer.discard_before(
                    max(
                        0,
                        frame_index - self.history_frames,
                    )
                )

                if not self.buffer.put(
                    decoded_index,
                    decoded,
                ):
                    raise RuntimeError("Impossible de reconstruire le tampon après le seek.")

            if decoded_index < frame_index:
                continue

            if decoded_index == frame_index:
                self._next_sequential_index = decoded_index + 1
                self.frame_ready.emit(
                    decoded_index,
                    decoded,
                )
                self.seek_completed.emit(decoded_index)
                self._emit_buffer_state()
                return

            # On a dépassé l'image demandée.
            raise RuntimeError(f"Le seek vidéo a dépassé l'image {frame_index + 1}.")

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

    def _calculate_effective_fps(self, frame_count: int | None = None) -> float:
        count = frame_count if frame_count is not None else self.part.frame_count
        duration_seconds = (self.part.video_end_time - self.part.video_start_time).total_seconds()
        if duration_seconds > 0 and count > 1:
            return count / duration_seconds
        if self.part.recording_fps > 0:
            return self.part.recording_fps
        return 20.0

    def _target_ahead_frame_count(self) -> int:
        with self._state_lock:
            playing = self._playing
            speed = self._playback_speed

        target_seconds = 3.0 if not playing else min(8.0, self.target_ahead_seconds + speed)
        requested_frames = round(self._effective_fps_value * target_seconds * max(1.0, speed))
        bytes_per_frame = self.part.frame_width * self.part.frame_height * 3
        if bytes_per_frame <= 0:
            return max(1, requested_frames)

        capacity = max(2, self.buffer.maximum_bytes // bytes_per_frame)
        maximum_ahead = max(1, capacity - self.history_frames - 4)
        return min(requested_frames, maximum_ahead)

    def _estimated_frame_bytes(self) -> int:
        return max(1, self.part.frame_width * self.part.frame_height * 3)

    def _has_capacity_for_next_frame(self) -> bool:
        return self.buffer.can_fit(self._estimated_frame_bytes())

    def _mark_end_of_stream(self) -> None:
        self._end_of_stream = True
        actual_count = self._next_sequential_index
        if actual_count > 0:
            self._total_frame_count = actual_count
        if not self._end_signal_emitted:
            self._end_signal_emitted = True
            self.stream_ended.emit(self._total_frame_count)

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
            self.buffer_changed.emit(indices[0], indices[-1], self.buffer.used_bytes)

    def _index_from_pts(
        self,
        frame: av.VideoFrame,
    ) -> int | None:
        if self._stream is None:
            return None

        time_base = frame.time_base or self._stream.time_base

        if frame.pts is None or time_base is None:
            return None

        stream_start = self._stream.start_time or 0

        position_seconds = max(
            0.0,
            float((frame.pts - stream_start) * time_base),
        )

        return max(
            0,
            round(position_seconds * self._effective_fps_value),
        )
