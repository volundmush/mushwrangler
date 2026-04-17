from __future__ import annotations

from PySide6.QtWidgets import QLabel, QSplitter, QStackedWidget, QTreeWidget, QTreeWidgetItem

from mushwrangler.settings import SettingsData


class SettingsManager(QSplitter):
    def __init__(self, settings: SettingsData, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings

        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabel("Settings, Worlds, Characters")

        self.right = QStackedWidget(self)

        self.global_page = QLabel("Global settings will go here.", self.right)
        self.right.addWidget(self.global_page)

        root = QTreeWidgetItem(self.tree)
        root.setText(0, "Global Settings")
        self.tree.addTopLevelItem(root)

        for world in self.settings.worlds.values():
            w_item = QTreeWidgetItem(root)
            w_item.setText(0, world.name)

            for character in self.settings.characters.values():
                if character.world_id != world.id:
                    continue
                c_item = QTreeWidgetItem(w_item)
                c_item.setText(0, character.name)

        root.setExpanded(True)
        self.tree.expandAll()
