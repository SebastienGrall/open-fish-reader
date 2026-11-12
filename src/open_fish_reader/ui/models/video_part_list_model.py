from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from .video_part_list_item import VideoPartListItem, VideoPartStatus


class VideoPartRoles:
    ITEM = Qt.ItemDataRole.UserRole + 1
    STATUS = Qt.ItemDataRole.UserRole + 2
    START_TIME = Qt.ItemDataRole.UserRole + 3
    DURATION_MS = Qt.ItemDataRole.UserRole + 4
    OBSERVATION_COUNT = Qt.ItemDataRole.UserRole + 5


class VideoPartListModel(QAbstractListModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[VideoPartListItem] = []

    def rowCount(
        self,
        parent: QModelIndex | None = None,
    ) -> int:
        if parent is not None and parent.isValid():
            return 0

        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return item.video_start_time.strftime("%H:%M:%S")
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip(item)
        if role == VideoPartRoles.ITEM:
            return item
        if role == VideoPartRoles.STATUS:
            return item.status.value
        if role == VideoPartRoles.START_TIME:
            return item.video_start_time
        if role == VideoPartRoles.DURATION_MS:
            return item.duration_ms
        if role == VideoPartRoles.OBSERVATION_COUNT:
            return item.observation_count
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            VideoPartRoles.ITEM: b"item",
            VideoPartRoles.STATUS: b"status",
            VideoPartRoles.START_TIME: b"startTime",
            VideoPartRoles.DURATION_MS: b"durationMs",
            VideoPartRoles.OBSERVATION_COUNT: b"observationCount",
        }

    def set_items(self, items: list[VideoPartListItem]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def item_at(self, row: int) -> VideoPartListItem | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def row_for_video_part_id(self, video_part_id: int) -> int | None:
        for row, item in enumerate(self._items):
            if item.video_part_id == video_part_id:
                return row
        return None

    def update_status(
        self,
        row: int,
        status: VideoPartStatus,
        observation_count: int | None = None,
        error_message: str | None = None,
    ) -> None:
        item = self.item_at(row)
        if item is None:
            return
        count = item.observation_count if observation_count is None else max(0, observation_count)
        self._items[row] = replace(
            item,
            status=status,
            observation_count=count,
            error_message=error_message,
        )
        index = self.index(row, 0)
        self.dataChanged.emit(index, index, [])

    @staticmethod
    def _tooltip(item: VideoPartListItem) -> str:
        lines = [
            item.video_start_time.isoformat(timespec="milliseconds"),
            item.video_path.name,
            f"Événement : {item.source_event_id}",
            f"Partie : {item.part_number}",
            f"Images déclarées : {item.frame_count}",
            f"Statut : {item.status.value}",
            f"Observations : {item.observation_count}",
        ]
        if item.error_message:
            lines.append(f"Erreur : {item.error_message}")
        return "\n".join(lines)
