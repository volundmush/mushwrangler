from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QMdiArea, QMdiSubWindow

from mushwrangler.settings import SettingsData
from mushwrangler.widgets.client_instance import MUClientInstance
from mushwrangler.widgets.settings_manager import SettingsManager


class MUSHWranglerWindow(QMainWindow):
    def __init__(self, settings: SettingsData, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings

        self.setObjectName("mainwindow")
        self.setWindowTitle("MUSHWrangler")
        self.resize(1280, 800)

        self.mdi_area = QMdiArea(self)
        self.setCentralWidget(self.mdi_area)

        self._add_seed_windows()

    def _add_seed_windows(self) -> None:
        first_character = next(iter(self.settings.characters.values()), None)
        if first_character is not None:
            world = self.settings.worlds[first_character.world_id]
            client = MUClientInstance(first_character, world, self)

            client_sub = QMdiSubWindow(self.mdi_area)
            client_sub.setWidget(client)
            client_sub.setWindowTitle(f"{world.name} - {first_character.name}")
            self.mdi_area.addSubWindow(client_sub)
            client_sub.resize(820, 520)
            client_sub.show()

        settings_widget = SettingsManager(self.settings, self)
        settings_sub = QMdiSubWindow(self.mdi_area)
        settings_sub.setWidget(settings_widget)
        settings_sub.setWindowTitle("Settings")
        self.mdi_area.addSubWindow(settings_sub)
        settings_sub.resize(520, 560)
        settings_sub.move(80, 80)
        settings_sub.show()
