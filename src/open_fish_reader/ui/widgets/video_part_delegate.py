from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from ..models.video_part_list_item import VideoPartListItem, VideoPartStatus
from ..models.video_part_list_model import VideoPartRoles

_STATUS_STYLE = {
    VideoPartStatus.UNREAD: ("○", QColor("#7b8794")),
    VideoPartStatus.IN_PROGRESS: ("◐", QColor("#d97706")),
    VideoPartStatus.READ: ("✓", QColor("#238636")),
    VideoPartStatus.OBSERVED: ("●", QColor("#0969da")),
    VideoPartStatus.REVIEW: ("!", QColor("#d97706")),
    VideoPartStatus.ERROR: ("×", QColor("#cf222e")),
}


class VideoPartDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        rect = option.rect.adjusted(6, 2, -6, -2)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if selected:
            painter.fillRect(option.rect, option.palette.highlight())
            text_color = option.palette.highlightedText().color()
            painter.fillRect(
                QRect(option.rect.left(), option.rect.top(), 4, option.rect.height()),
                QColor("#0969da"),
            )
        else:
            text_color = option.palette.text().color()

        item = index.data(VideoPartRoles.ITEM)
        if not isinstance(item, VideoPartListItem):
            painter.restore()
            return

        icon, status_color = _STATUS_STYLE[item.status]
        if item.observation_count > 0:
            icon = str(min(item.observation_count, 99))
            status_color = QColor("#0969da")

        icon_rect = QRect(rect.left(), rect.top(), 28, rect.height())
        time_rect = QRect(icon_rect.right() + 8, rect.top(), 82, rect.height())
        duration_rect = QRect(
            time_rect.right() + 8, rect.top(), rect.right() - time_rect.right() - 8, rect.height()
        )

        icon_font = QFont(option.font)
        icon_font.setBold(True)
        painter.setFont(icon_font)
        painter.setPen(QPen(status_color))
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, icon)

        painter.setFont(option.font)
        painter.setPen(QPen(text_color))
        painter.drawText(
            time_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            item.video_start_time.strftime("%H:%M:%S"),
        )
        painter.drawText(
            duration_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
            format_duration(item.duration_ms),
        )
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return QSize(230, 34)


def format_duration(duration_ms: int) -> str:
    total_ms = max(0, duration_ms)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    return f"{minutes:02d}:{seconds:02d},{milliseconds:03d}"
