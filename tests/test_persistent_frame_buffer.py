from datetime import UTC, datetime

from PySide6.QtGui import QImage

from open_fish_reader.video.frame import DecodedFrame
from open_fish_reader.video.persistent_frame_buffer import PersistentFrameBuffer


def make_frame(index: int, size: int = 64) -> DecodedFrame:
    return DecodedFrame(
        image=QImage(size, size, QImage.Format.Format_RGB888),
        frame_number=index,
        pts=index,
        position_ms=index * 40,
        absolute_timestamp=datetime.now(UTC),
    )


def test_buffer_is_bounded() -> None:
    frame = make_frame(0)
    frame_bytes = frame.image.bytesPerLine() * frame.image.height()
    buffer = PersistentFrameBuffer(frame_bytes * 2)

    buffer.put(0, frame)
    buffer.put(1, make_frame(1))
    buffer.put(2, make_frame(2))

    assert buffer.used_bytes <= buffer.maximum_bytes
    assert buffer.frame_count == 2
    assert buffer.get(0) is None


def test_protect_range_refreshes_history() -> None:
    frame = make_frame(0)
    frame_bytes = frame.image.bytesPerLine() * frame.image.height()
    buffer = PersistentFrameBuffer(frame_bytes * 3)

    buffer.put(0, frame)
    buffer.put(1, make_frame(1))
    buffer.put(2, make_frame(2))
    buffer.protect_range(0, 0)
    buffer.put(3, make_frame(3))

    assert buffer.get(0) is not None
    assert buffer.get(1) is None
