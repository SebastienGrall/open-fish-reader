from open_fish_reader.ui.widgets.video_part_delegate import format_duration


def test_formats_short_duration() -> None:
    assert format_duration(661) == "00:00,661"


def test_formats_minutes() -> None:
    assert format_duration(257_828) == "04:17,828"


def test_formats_hours() -> None:
    assert format_duration(3_661_234) == "01:01:01,234"
