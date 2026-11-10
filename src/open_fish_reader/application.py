import sys

from PySide6.QtWidgets import QApplication

from .core.logging_config import configure_logging
from .core.paths import ensure_app_directories
from .ui.main_window import MainWindow
from .version import APP_NAME, APP_VERSION, ORGANIZATION_NAME


def main() -> int:
    ensure_app_directories()
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORGANIZATION_NAME)
    window = MainWindow()
    window.showMaximized()
    return app.exec()
