from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from ..core.constants import (
    MAX_PLAYBACK_SPEED,
    MIN_PLAYBACK_SPEED,
    PLAYBACK_SPEED_STEP,
)


class PlaybackController(QObject):
    frame_changed = Signal(int)
    playing_changed = Signal(bool)
    speed_changed = Signal(float)
    sequence_finished = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setTimerType(self._timer.timerType().PreciseTimer)
        self._timer.timeout.connect(self._advance)

        self._frame_count = 0
        self._current_index = -1
        self._fps = 20.0
        self._speed = 1.0
        self._playing = False

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def current_index(self) -> int:
        return self._current_index

    def load_sequence(
        self,
        frame_count: int,
        fps: float,
        initial_index: int = 0,
    ) -> None:
        self.pause()
        self._frame_count = max(0, frame_count)
        self._fps = fps if fps > 0 else 20.0
        if self._frame_count == 0:
            self._current_index = -1
            return
        self._current_index = min(max(0, initial_index), self._frame_count - 1)
        self.frame_changed.emit(self._current_index)

    def set_current_index(self, index: int) -> None:
        if self._playing or self._frame_count == 0:
            return
        bounded = min(max(0, index), self._frame_count - 1)
        if bounded == self._current_index:
            return
        self._current_index = bounded
        self.frame_changed.emit(self._current_index)

    @Slot()
    def toggle(self) -> None:
        if self._playing:
            self.pause()
        else:
            self.play()

    @Slot()
    def play(self) -> None:
        if self._playing or self._frame_count == 0:
            return
        if self._current_index >= self._frame_count - 1:
            self.sequence_finished.emit()
            return
        self._playing = True
        self._timer.start(self._interval_ms())
        self.playing_changed.emit(True)

    @Slot()
    def pause(self) -> None:
        if not self._playing:
            return
        self._timer.stop()
        self._playing = False
        self.playing_changed.emit(False)

    def set_speed(self, speed: float) -> None:
        bounded = min(MAX_PLAYBACK_SPEED, max(MIN_PLAYBACK_SPEED, speed))
        rounded = round(bounded / PLAYBACK_SPEED_STEP) * PLAYBACK_SPEED_STEP
        if rounded == self._speed:
            return
        self._speed = rounded
        if self._playing:
            self._timer.start(self._interval_ms())
        self.speed_changed.emit(self._speed)

    @Slot()
    def increase_speed(self) -> None:
        self.set_speed(self._speed + PLAYBACK_SPEED_STEP)

    @Slot()
    def decrease_speed(self) -> None:
        self.set_speed(self._speed - PLAYBACK_SPEED_STEP)

    @Slot()
    def reset_speed(self) -> None:
        self.set_speed(1.0)

    def _interval_ms(self) -> int:
        return max(1, round(1000 / (self._fps * self._speed)))

    @Slot()
    def _advance(self) -> None:
        if not self._playing:
            return
        next_index = self._current_index + 1
        if next_index >= self._frame_count:
            self.pause()
            self.sequence_finished.emit()
            return
        self._current_index = next_index
        self.frame_changed.emit(self._current_index)
        if self._current_index >= self._frame_count - 1:
            self.pause()
            self.sequence_finished.emit()
