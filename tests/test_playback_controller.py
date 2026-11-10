from open_fish_reader.video.playback_controller import PlaybackController


def test_load_sequence_emits_initial_frame(qtbot) -> None:
    controller = PlaybackController()
    with qtbot.waitSignal(controller.frame_changed, timeout=500) as blocker:
        controller.load_sequence(frame_count=12, fps=20.0)
    assert blocker.args == [0]
    assert controller.current_index == 0


def test_speed_is_clamped() -> None:
    controller = PlaybackController()
    controller.set_speed(50.0)
    assert controller.speed == 10.0
    controller.set_speed(0.1)
    assert controller.speed == 0.5


def test_manual_index_is_blocked_during_playback(qtbot) -> None:
    controller = PlaybackController()
    controller.load_sequence(frame_count=12, fps=20.0)
    controller.play()
    controller.set_current_index(7)
    assert controller.current_index == 0
    controller.pause()
