from __future__ import annotations

from datetime import date, datetime, time, timedelta

from PySide6.QtCore import QDateTime, Signal
from PySide6.QtWidgets import (
    QDateTimeEdit,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class PassageDateTimeFilter(QWidget):
    refresh_requested = Signal()

    def __init__(self, current_day: date | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        selected_day = current_day or datetime.now().date()

        self.start_edit = QDateTimeEdit()
        self.end_edit = QDateTimeEdit()
        for editor in (self.start_edit, self.end_edit):
            editor.setCalendarPopup(True)
            editor.setDisplayFormat("dd/MM/yyyy HH:mm")

        self.set_full_day(selected_day)

        full_day_button = QPushButton("Journée entière")
        previous_hour_button = QPushButton("− 1 heure")
        next_hour_button = QPushButton("+ 1 heure")
        refresh_button = QPushButton("Actualiser")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Du"))
        layout.addWidget(self.start_edit)
        layout.addWidget(QLabel("Au"))
        layout.addWidget(self.end_edit)
        layout.addWidget(full_day_button)
        layout.addWidget(previous_hour_button)
        layout.addWidget(next_hour_button)
        layout.addWidget(refresh_button)

        full_day_button.clicked.connect(self._set_selected_full_day)
        previous_hour_button.clicked.connect(lambda: self.shift_hours(-1))
        next_hour_button.clicked.connect(lambda: self.shift_hours(1))
        refresh_button.clicked.connect(self.refresh_requested.emit)
        self.start_edit.dateTimeChanged.connect(self._keep_range_valid)

    def period(self) -> tuple[datetime, datetime]:
        start_at = self.start_edit.dateTime().toPython().astimezone()
        end_inclusive = self.end_edit.dateTime().toPython().astimezone()
        # L'interface est à la minute. La requête utilise une borne exclusive
        # une minute après la minute de fin affichée.
        return start_at, end_inclusive + timedelta(minutes=1)

    def set_full_day(self, selected_day: date) -> None:
        timezone = datetime.now().astimezone().tzinfo
        start = datetime.combine(selected_day, time.min, timezone)
        end = datetime.combine(selected_day, time(23, 59), timezone)
        self.start_edit.setDateTime(QDateTime(start))
        self.end_edit.setDateTime(QDateTime(end))

    def shift_hours(self, hours: int) -> None:
        seconds = hours * 3600
        self.start_edit.setDateTime(self.start_edit.dateTime().addSecs(seconds))
        self.end_edit.setDateTime(self.end_edit.dateTime().addSecs(seconds))
        self.refresh_requested.emit()

    def _set_selected_full_day(self) -> None:
        self.set_full_day(self.start_edit.dateTime().date().toPython())
        self.refresh_requested.emit()

    def _keep_range_valid(self) -> None:
        if self.end_edit.dateTime() < self.start_edit.dateTime():
            self.end_edit.setDateTime(self.start_edit.dateTime())
