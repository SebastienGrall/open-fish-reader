from open_fish_reader.ui.models.taxon_table_model import normalize_shortcut


def test_shortcut_is_normalized() -> None:
    assert normalize_shortcut(" a ") == "A"
    assert normalize_shortcut("") is None
