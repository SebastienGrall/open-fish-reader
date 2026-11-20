from datetime import date

from open_fish_reader.ui.widgets.passage_datetime_filter import PassageDateTimeFilter


def test_full_day_period_is_end_exclusive(qtbot) -> None:
    widget = PassageDateTimeFilter(date(2026, 11, 20))
    qtbot.addWidget(widget)
    start_at, end_at = widget.period()
    assert start_at.strftime("%Y-%m-%d %H:%M") == "2026-11-20 00:00"
    assert end_at.strftime("%Y-%m-%d %H:%M") == "2026-11-21 00:00"
