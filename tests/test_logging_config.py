import logging

from open_fish_reader.core.logging_config import configure_logging


def test_configure_logging_creates_rotating_log(monkeypatch, tmp_path) -> None:
    class Paths:
        logs = tmp_path

    monkeypatch.setattr(
        "open_fish_reader.core.logging_config.get_app_paths",
        lambda: Paths(),
    )
    path = configure_logging()
    logging.getLogger("test").warning("message test")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert path.exists()
    assert "message test" in path.read_text(encoding="utf-8")
