from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QLabel, QListView, QVBoxLayout, QWidget

from ...domain.indexed_video_part import IndexedVideoPart
from ..models.video_part_list_item import VideoPartListItem, VideoPartStatus
from ..models.video_part_list_model import VideoPartListModel
from .video_part_delegate import VideoPartDelegate


class VideoPartPanel(QWidget):
    open_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(225)
        self.setMaximumWidth(420)

        title = QLabel("Séquences")
        title.setStyleSheet("font-size: 15px; font-weight: 600; padding: 4px;")
        self.summary_label = QLabel("0 fichier")
        self.summary_label.setStyleSheet("color: palette(mid); padding: 0 4px 4px 4px;")

        self.model = VideoPartListModel(self)
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(VideoPartDelegate(self.list_view))
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setAlternatingRowColors(True)
        self.list_view.doubleClicked.connect(self._emit_open_request)
        self.list_view.activated.connect(self._emit_open_request)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(title)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.list_view, stretch=1)

    def set_parts(self, parts: list[IndexedVideoPart]) -> None:
        self.model.set_items([VideoPartListItem.from_indexed_part(part) for part in parts])
        count = len(parts)
        self.summary_label.setText(f"{count} fichier" + ("s" if count != 1 else ""))
        if count:
            self.set_current_row(0)

    def set_current_row(self, row: int) -> None:
        if not 0 <= row < self.model.rowCount():
            return
        index = self.model.index(row, 0)
        self.list_view.setCurrentIndex(index)
        self.list_view.scrollTo(index, QAbstractItemView.ScrollHint.EnsureVisible)

    def mark_in_progress(self, row: int) -> None:
        item = self.model.item_at(row)
        if item is None or item.status in (
            VideoPartStatus.ERROR,
            VideoPartStatus.OBSERVED,
            VideoPartStatus.READ,
        ):
            return
        self.model.update_status(row, VideoPartStatus.IN_PROGRESS)

    def mark_read(self, row: int) -> None:
        item = self.model.item_at(row)
        if item is None or item.status in (VideoPartStatus.ERROR, VideoPartStatus.OBSERVED):
            return
        self.model.update_status(row, VideoPartStatus.READ)

    def mark_error(self, row: int, message: str) -> None:
        self.model.update_status(row, VideoPartStatus.ERROR, error_message=message)

    def set_observation_count(self, row: int, count: int) -> None:
        status = VideoPartStatus.OBSERVED if count > 0 else VideoPartStatus.READ
        self.model.update_status(row, status, observation_count=count)

    def _emit_open_request(self, index: QModelIndex) -> None:
        if index.isValid():
            self.open_requested.emit(index.row())
