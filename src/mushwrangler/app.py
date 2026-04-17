from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from mushwrangler.main_window import MUSHWranglerWindow
from mushwrangler.settings import seed_demo_settings


def main() -> int:
    app = QApplication(sys.argv)

    settings = seed_demo_settings()
    window = MUSHWranglerWindow(settings)
    window.show()

    return app.exec()
