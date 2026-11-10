import logging
from logging.handlers import RotatingFileHandler

from .paths import get_app_paths


def configure_logging() -> None:
    p = get_app_paths().logs / "open-fish-reader.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(p, maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(handler)
