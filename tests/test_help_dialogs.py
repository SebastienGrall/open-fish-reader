from open_fish_reader.ui.dialogs.keyboard_shortcuts_dialog import (
    KeyboardShortcutsDialog,
)
from open_fish_reader.ui.dialogs.user_guide_dialog import UserGuideDialog


def test_help_dialogs_can_be_created(qtbot) -> None:
    guide = UserGuideDialog()
    shortcuts = KeyboardShortcutsDialog()
    qtbot.addWidget(guide)
    qtbot.addWidget(shortcuts)
    assert guide.windowTitle() == "Guide rapide"
    assert shortcuts.windowTitle() == "Raccourcis clavier"
