from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ...domain.indexed_video_part import IndexedVideoPart
from ...video.video_decoder import VideoDecodeError, VideoDecoder


class FrameSequenceWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, part: IndexedVideoPart) -> None:
        super().__init__()
        self.part = part

    @Slot()
    def run(self) -> None:
        try:
            self.completed.emit(VideoDecoder().decode_all_frames(self.part))
        except VideoDecodeError as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()
