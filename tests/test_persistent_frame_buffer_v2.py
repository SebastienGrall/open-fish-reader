from datetime import UTC, datetime

from PySide6.QtGui import QImage

from open_fish_reader.video.frame import DecodedFrame
from open_fish_reader.video.persistent_frame_buffer import PersistentFrameBuffer


def make_frame(index: int) -> DecodedFrame:
    return DecodedFrame(
        image=QImage(64, 64, QImage.Format.Format_RGB888),
        frame_number=index,
        pts=index,
        position_ms=index * 40,
        absolute_timestamp=datetime.now(UTC),
    )


def test_fifo_does_not_evict_future_frames_on_get() -> None:
    first = make_frame(0)
    size = first.image.bytesPerLine() * first.image.height()
    buffer = PersistentFrameBuffer(size * 3)
    buffer.put(0, first)
    buffer.put(1, make_frame(1))
    buffer.put(2, make_frame(2))
    assert buffer.get(0) is first
    assert buffer.put(3, make_frame(3)) is False
    buffer.discard_before(1)
    assert buffer.put(3, make_frame(3)) is True
    assert buffer.indices() == (1, 2, 3)
