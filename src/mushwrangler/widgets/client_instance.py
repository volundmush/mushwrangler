from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QSplitter, QTextEdit

from mushwrangler.models import Character, World


class MUClientInstance(QSplitter):
    def __init__(self, character: Character, world: World, parent=None) -> None:
        super().__init__(parent)
        self.character = character
        self.world = world

        self.setOrientation(Qt.Orientation.Vertical)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)

        self.input = QTextEdit(self)

        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.output.setFont(mono)
        self.input.setFont(mono)

        self.output.append(f"Connected profile: {world.name} / {character.name}")
        self.output.append(
            f"Target host: {world.host.address}:{world.host.port} (tls={world.host.tls})"
        )
