from __future__ import annotations

import logging
import platform
import sqlite3
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

from PySide6 import __version__ as pyside_version

from ..version import APP_NAME, APP_VERSION
from .paths import get_app_paths

LOG_FILE_NAME = "open-fish-reader.log"
LOG_FORMAT = "%(asctime)s.%(msecs)03d | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> Path:
    log_folder = get_app_paths().logs
    log_folder.mkdir(parents=True, exist_ok=True)
    log_path = log_folder / LOG_FILE_NAME

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Évite de dupliquer les lignes si main() est rappelé dans un test.
    for handler in list(root_logger.handlers):
        if getattr(handler, "_open_fish_reader_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler._open_fish_reader_handler = True  # type: ignore[attr-defined]
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # Conserve aussi les messages dans la console pendant le développement.
    console_handler = logging.StreamHandler()
    console_handler._open_fish_reader_handler = True  # type: ignore[attr-defined]
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(console_handler)

    logger = logging.getLogger(__name__)
    logger.info("Démarrage de %s %s", APP_NAME, APP_VERSION)
    logger.info(
        "Environnement : Python %s | PySide6 %s | SQLite %s | %s %s",
        platform.python_version(),
        pyside_version,
        sqlite3.sqlite_version,
        platform.system(),
        platform.release(),
    )
    logger.info("Journal : %s", log_path)
    return log_path


def install_exception_hook() -> None:
    logger = logging.getLogger("open_fish_reader.unhandled")
    previous_hook = sys.excepthook

    def handle_exception(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        if issubclass(exception_type, KeyboardInterrupt):
            previous_hook(exception_type, exception, traceback)
            return
        logger.critical(
            "Exception non gérée",
            exc_info=(exception_type, exception, traceback),
        )
        previous_hook(exception_type, exception, traceback)

    sys.excepthook = handle_exception
