from open_fish_reader.ui.models.passage_table_model import PassageTableModel


def test_formats_observed_at_in_french(qtbot) -> None:
    model = PassageTableModel()
    model.set_rows(
        [
            {
                "observed_at": "2026-11-20T09:48:31.127+01:00",
                "tax_code": "AGJ",
                "common_name": "Anguille jaune",
                "individual_count": 1,
                "direction": 1,
                "confidence": "certain",
                "needs_review": 0,
                "length_mm": None,
                "glass_position": "middle",
                "comment": None,
                "video_file_name": "part.mp4",
                "frame_number": 0,
            }
        ]
    )
    assert model.data(model.index(0, 0)) == "20/11/2026 09:48:31.127"
