from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .core.logging_config import configure_logging, install_exception_hook
from .core.paths import ensure_app_directories
from .core.resources import resource_path
from .ui.main_window import MainWindow
from .version import APP_NAME, APP_VERSION, ORGANIZATION_NAME


def main() -> int:
    ensure_app_directories()
    configure_logging()
    install_exception_hook()

    logger = logging.getLogger(__name__)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setWindowIcon(QIcon(str(resource_path("icons/open_fish_reader.ico"))))

    window = MainWindow()
    window.showMaximized()
    exit_code = app.exec()
    logger.info("Arrêt de %s, code=%s", APP_NAME, exit_code)
    logging.shutdown()
    return exit_code
