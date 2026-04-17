from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from mushwrangler.main_window import MUSHWranglerWindow
from mushwrangler.settings import load_settings, save_settings, seed_demo_settings


def main() -> int:
    app = QApplication(sys.argv)

    settings = load_settings()
    if not settings.worlds or not settings.characters:
        settings = seed_demo_settings()
        save_settings(settings)

    app.aboutToQuit.connect(lambda: save_settings(settings))

    window = MUSHWranglerWindow(settings)
    window.show()

    return app.exec()
