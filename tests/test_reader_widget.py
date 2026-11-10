from open_fish_reader.ui.widgets.reader_widget import ReaderWidget


def test_reader_widget_initial_state(qtbot) -> None:
    widget = ReaderWidget()
    qtbot.addWidget(widget)

    assert widget.previous_file_button.isEnabled() is False
    assert widget.next_file_button.isEnabled() is False
    assert widget.play_pause_button.isEnabled() is False
