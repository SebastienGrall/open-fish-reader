from __future__ import annotations

from fractions import Fraction

import av
from PySide6.QtGui import QImage

from ..domain.indexed_video_part import IndexedVideoPart
from .frame import DecodedFrame


class VideoDecodeError(RuntimeError):
    """La vidéo ne peut pas être ouverte ou décodée."""


class VideoDecoder:
    def decode_first_frame(self, part: IndexedVideoPart) -> DecodedFrame:
        if not part.video_path.is_file():
            raise VideoDecodeError(f"Vidéo introuvable : {part.video_path}")

        try:
            with av.open(str(part.video_path)) as container:
                stream = container.streams.video[0]
                for frame_number, frame in enumerate(container.decode(stream)):
                    return self._convert_frame(part, frame, frame_number, stream.time_base)
        except (av.AVError, IndexError, OSError) as error:
            raise VideoDecodeError(
                f"Impossible de décoder {part.video_path.name} : {error}"
            ) from error

        raise VideoDecodeError(f"Aucune image dans {part.video_path.name}.")

    @staticmethod
    def _convert_frame(
        part: IndexedVideoPart,
        frame: av.VideoFrame,
        frame_number: int,
        stream_time_base: Fraction | None,
    ) -> DecodedFrame:
        array = frame.to_ndarray(format="rgb24")
        height, width, _channels = array.shape
        image = QImage(
            array.data, width, height, array.strides[0], QImage.Format.Format_RGB888
        ).copy()
        time_base = frame.time_base or stream_time_base
        position_seconds = (
            float(frame.pts * time_base) if frame.pts is not None and time_base else 0.0
        )
        position_ms = max(0, round(position_seconds * 1000))
        return DecodedFrame(
            image=image,
            frame_number=frame_number,
            pts=frame.pts,
            position_ms=position_ms,
            absolute_timestamp=part.video_start_time
            + __import__("datetime").timedelta(milliseconds=position_ms),
        )
