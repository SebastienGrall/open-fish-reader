from open_fish_reader.ui.widgets.quick_observation_panel import QuickObservationPanel


def test_panel_defaults(qtbot) -> None:
    panel = QuickObservationPanel()
    qtbot.addWidget(panel)
    assert panel.count_spin.value() == 1
    assert panel.length_spin.value() == 0
    assert panel.glass_position_combo.currentData() == "middle"
    assert panel.confidence_combo.currentData() == "certain"
    assert panel.review_checkbox.isChecked() is False
    assert panel.upstream_button.isEnabled() is False
