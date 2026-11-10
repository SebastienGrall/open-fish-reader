from __future__ import annotations

from datetime import timedelta
from fractions import Fraction

import av
from PySide6.QtGui import QImage

from ..domain.indexed_video_part import IndexedVideoPart
from .cache_policy import decide_full_cache, format_megabytes
from .frame import DecodedFrame


class VideoDecodeError(RuntimeError):
    """La vidéo ne peut pas être ouverte ou décodée."""


class VideoTooLargeForMemoryCacheError(VideoDecodeError):
    """La vidéo doit être lue avec un cache glissant et non en cache complet."""


class VideoDecoder:
    def decode_all_frames(
        self,
        part: IndexedVideoPart,
    ) -> list[DecodedFrame]:
        decision = decide_full_cache(part)
        if not decision.allow_full_cache:
            raise VideoTooLargeForMemoryCacheError(
                f"{part.video_path.name} ne sera pas chargé entièrement en mémoire. "
                f"Estimation : {format_megabytes(decision.estimated_bytes)}, "
                f"durée : {decision.duration_seconds:.1f} s. "
                "Le lecteur à cache glissant sera utilisé dans une prochaine étape."
            )

        if not part.video_path.is_file():
            raise VideoDecodeError(f"Vidéo introuvable : {part.video_path}")

        decoded_frames: list[DecodedFrame] = []

        try:
            with av.open(str(part.video_path)) as container:
                if not container.streams.video:
                    raise VideoDecodeError(f"Aucun flux vidéo dans {part.video_path.name}.")

                stream = container.streams.video[0]
                for frame_number, frame in enumerate(container.decode(stream)):
                    decoded_frames.append(
                        self._convert_frame(
                            part,
                            frame,
                            frame_number,
                            stream.time_base,
                        )
                    )

        except VideoDecodeError:
            raise
        except (av.error.FFmpegError, OSError, IndexError) as error:
            raise VideoDecodeError(
                f"Impossible de décoder {part.video_path.name} : {error}"
            ) from error

        if not decoded_frames:
            raise VideoDecodeError(f"Aucune image dans {part.video_path.name}.")

        return decoded_frames

    def decode_first_frame(
        self,
        part: IndexedVideoPart,
    ) -> DecodedFrame:
        if not part.video_path.is_file():
            raise VideoDecodeError(f"Vidéo introuvable : {part.video_path}")

        try:
            with av.open(str(part.video_path)) as container:
                if not container.streams.video:
                    raise VideoDecodeError(f"Aucun flux vidéo dans {part.video_path.name}.")
                stream = container.streams.video[0]
                for frame_number, frame in enumerate(container.decode(stream)):
                    return self._convert_frame(
                        part,
                        frame,
                        frame_number,
                        stream.time_base,
                    )
        except VideoDecodeError:
            raise
        except (av.error.FFmpegError, OSError, IndexError) as error:
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
            array.data,
            width,
            height,
            array.strides[0],
            QImage.Format.Format_RGB888,
        ).copy()

        time_base = frame.time_base or stream_time_base
        if frame.pts is not None and time_base is not None:
            position_seconds = float(frame.pts * time_base)
        else:
            position_seconds = frame_number / part.recording_fps

        position_ms = max(0, round(position_seconds * 1000))
        return DecodedFrame(
            image=image,
            frame_number=frame_number,
            pts=frame.pts,
            position_ms=position_ms,
            absolute_timestamp=(part.video_start_time + timedelta(milliseconds=position_ms)),
        )
