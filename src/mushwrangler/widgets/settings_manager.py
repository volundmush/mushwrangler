from __future__ import annotations

from uuid import UUID, uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mushwrangler.models import Character, Host, World
from mushwrangler.settings import (
    SettingsData,
    delete_character,
    delete_world,
    save_character,
    save_world,
)


class WorldEditor(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._world: World | None = None

        layout = QFormLayout(self)
        self.name_edit = QLineEdit(self)
        self.host_edit = QLineEdit(self)
        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1, 65535)
        self.tls_combo = QComboBox(self)
        self.tls_combo.addItems(["False", "True"])

        layout.addRow("Name", self.name_edit)
        layout.addRow("Host", self.host_edit)
        layout.addRow("Port", self.port_spin)
        layout.addRow("TLS", self.tls_combo)

        self.name_edit.editingFinished.connect(self._apply)
        self.host_edit.editingFinished.connect(self._apply)
        self.port_spin.valueChanged.connect(lambda _v: self._apply())
        self.tls_combo.currentIndexChanged.connect(lambda _i: self._apply())

    def set_world(self, world: World | None) -> None:
        self._world = world
        if world is None:
            self.name_edit.clear()
            self.host_edit.clear()
            self.port_spin.setValue(1)
            self.tls_combo.setCurrentIndex(0)
            self.setEnabled(False)
            return

        self.setEnabled(True)
        self.name_edit.setText(world.name)
        self.host_edit.setText(world.host.address)
        self.port_spin.setValue(world.host.port or 1)
        self.tls_combo.setCurrentIndex(1 if world.host.tls else 0)

    def _apply(self) -> None:
        if self._world is None:
            return
        self._world.name = self.name_edit.text().strip()
        self._world.host = Host(
            address=self.host_edit.text().strip(),
            port=self.port_spin.value(),
            tls=self.tls_combo.currentIndex() == 1,
        )
        save_world(self._world)
        self.changed.emit()


class CharacterEditor(QWidget):
    changed = Signal()
    rehome_requested = Signal(UUID, UUID)

    def __init__(self, settings: SettingsData, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._character: Character | None = None

        layout = QFormLayout(self)
        self.name_edit = QLineEdit(self)
        self.password_edit = QLineEdit(self)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_script_edit = QTextEdit(self)
        self.login_script_edit.setPlaceholderText(
            "One line per command. Use %NAME% and %PASSWORD% placeholders."
        )
        self.login_script_edit.setMaximumHeight(160)
        self.world_combo = QComboBox(self)
        self.split_input_check = QCheckBox("Enable second input split", self)
        self.launch_on_startup_check = QCheckBox("Launch on startup", self)

        layout.addRow("Name", self.name_edit)
        layout.addRow("Password", self.password_edit)
        layout.addRow("Startup Login Script", self.login_script_edit)
        layout.addRow("World", self.world_combo)
        layout.addRow("Input", self.split_input_check)
        layout.addRow("Startup", self.launch_on_startup_check)

        self.name_edit.editingFinished.connect(self._apply)
        self.password_edit.editingFinished.connect(self._apply)
        self.login_script_edit.textChanged.connect(self._apply)
        self.world_combo.currentIndexChanged.connect(self._on_world_changed)
        self.split_input_check.stateChanged.connect(lambda _s: self._apply())
        self.launch_on_startup_check.stateChanged.connect(lambda _s: self._apply())

    def refresh_worlds(self) -> None:
        selected = self.world_combo.currentData()
        self.world_combo.blockSignals(True)
        self.world_combo.clear()
        for world in self._settings.worlds.values():
            self.world_combo.addItem(world.name or str(world.id), world.id)
        if selected is not None:
            idx = self.world_combo.findData(selected)
            if idx >= 0:
                self.world_combo.setCurrentIndex(idx)
        self.world_combo.blockSignals(False)

    def set_character(self, character: Character | None) -> None:
        self._character = character
        self.refresh_worlds()
        if character is None:
            self.name_edit.clear()
            self.password_edit.clear()
            self.login_script_edit.clear()
            self.split_input_check.setChecked(False)
            self.launch_on_startup_check.setChecked(False)
            self.setEnabled(False)
            return

        self.setEnabled(True)
        self.name_edit.setText(character.name)
        self.password_edit.setText(character.password)
        script = character.login_script or character.login
        self.login_script_edit.blockSignals(True)
        self.login_script_edit.setPlainText(script)
        self.login_script_edit.blockSignals(False)
        self.split_input_check.setChecked(character.split_input)
        self.launch_on_startup_check.setChecked(character.launch_on_startup)
        idx = self.world_combo.findData(character.world_id)
        if idx >= 0:
            self.world_combo.setCurrentIndex(idx)

    def _apply(self) -> None:
        if self._character is None:
            return
        self._character.name = self.name_edit.text().strip()
        self._character.password = self.password_edit.text()
        self._character.login_script = self.login_script_edit.toPlainText()
        self._character.login = self._character.login_script
        self._character.split_input = self.split_input_check.isChecked()
        self._character.launch_on_startup = self.launch_on_startup_check.isChecked()
        save_character(self._character)
        self.changed.emit()

    def _on_world_changed(self, _index: int) -> None:
        if self._character is None:
            return
        target_world_id = self.world_combo.currentData()
        if target_world_id is None or target_world_id == self._character.world_id:
            return
        self.rehome_requested.emit(self._character.id, target_world_id)


class SettingsManager(QSplitter):
    data_changed = Signal()
    connect_character_requested = Signal(UUID)

    def __init__(self, settings: SettingsData, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._tree_items_by_world: dict[UUID, QTreeWidgetItem] = {}
        self._tree_items_by_character: dict[UUID, QTreeWidgetItem] = {}
        self._in_use_character_ids: set[UUID] = set()

        left = QWidget(self)
        left_layout = QVBoxLayout(left)

        self.tree = QTreeWidget(left)
        self.tree.setHeaderLabel("Settings / Worlds / Characters")
        self.tree.currentItemChanged.connect(self._on_tree_selection)
        left_layout.addWidget(self.tree)

        buttons = QHBoxLayout()
        self.new_world_btn = QPushButton("New World", left)
        self.copy_world_btn = QPushButton("Copy World", left)
        self.del_world_btn = QPushButton("Delete World", left)
        buttons.addWidget(self.new_world_btn)
        buttons.addWidget(self.copy_world_btn)
        buttons.addWidget(self.del_world_btn)
        left_layout.addLayout(buttons)

        buttons2 = QHBoxLayout()
        self.connect_char_btn = QPushButton("Connect", left)
        self.new_char_btn = QPushButton("New Character", left)
        self.copy_char_btn = QPushButton("Copy Character", left)
        self.del_char_btn = QPushButton("Delete Character", left)
        buttons2.addWidget(self.connect_char_btn)
        buttons2.addWidget(self.new_char_btn)
        buttons2.addWidget(self.copy_char_btn)
        buttons2.addWidget(self.del_char_btn)
        left_layout.addLayout(buttons2)

        self.right = QStackedWidget(self)
        self.global_page = QLabel("Global settings will go here.", self.right)
        self.right.addWidget(self.global_page)

        self.world_editor = WorldEditor(self.right)
        self.world_editor.changed.connect(self._refresh_tree_texts)
        self.right.addWidget(self.world_editor)

        self.character_editor = CharacterEditor(self.settings, self.right)
        self.character_editor.changed.connect(self._refresh_tree_texts)
        self.character_editor.rehome_requested.connect(self._rehome_character)
        self.right.addWidget(self.character_editor)

        self.addWidget(left)
        self.addWidget(self.right)
        self.setChildrenCollapsible(False)
        self.setSizes([420, 500])

        self.new_world_btn.clicked.connect(self._create_world)
        self.copy_world_btn.clicked.connect(self._copy_world)
        self.del_world_btn.clicked.connect(self._delete_world)
        self.connect_char_btn.clicked.connect(self._connect_selected_character)
        self.new_char_btn.clicked.connect(self._create_character)
        self.copy_char_btn.clicked.connect(self._copy_character)
        self.del_char_btn.clicked.connect(self._delete_character)

        self.rebuild_tree()

    def set_in_use_characters(self, character_ids: set[UUID]) -> None:
        self._in_use_character_ids = set(character_ids)

    def rebuild_tree(self) -> None:
        self.tree.clear()
        self._tree_items_by_world.clear()
        self._tree_items_by_character.clear()

        root = QTreeWidgetItem(self.tree)
        root.setText(0, "Global Settings")
        root.setData(0, Qt.ItemDataRole.UserRole, ("global", None))
        self.tree.addTopLevelItem(root)

        for world in self.settings.worlds.values():
            w_item = QTreeWidgetItem(root)
            w_item.setText(0, world.name or str(world.id))
            w_item.setData(0, Qt.ItemDataRole.UserRole, ("world", world.id))
            self._tree_items_by_world[world.id] = w_item

            for character in self.settings.characters.values():
                if character.world_id != world.id:
                    continue
                c_item = QTreeWidgetItem(w_item)
                c_item.setText(0, character.name or str(character.id))
                c_item.setData(0, Qt.ItemDataRole.UserRole, ("character", character.id))
                self._tree_items_by_character[character.id] = c_item

        root.setExpanded(True)
        self.tree.expandAll()
        self.character_editor.refresh_worlds()

    def _refresh_tree_texts(self) -> None:
        for world_id, item in self._tree_items_by_world.items():
            world = self.settings.worlds.get(world_id)
            if world is not None:
                item.setText(0, world.name or str(world.id))
                save_world(world)

        for char_id, item in self._tree_items_by_character.items():
            character = self.settings.characters.get(char_id)
            if character is not None:
                item.setText(0, character.name or str(character.id))
                save_character(character)

    def _selected(self) -> tuple[str, UUID | None]:
        item = self.tree.currentItem()
        if item is None:
            return "global", None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return "global", None
        return data

    def _selected_world_id(self) -> UUID | None:
        kind, obj_id = self._selected()
        if kind == "world":
            return obj_id
        if kind == "character" and obj_id is not None:
            character = self.settings.characters.get(obj_id)
            if character is not None:
                return character.world_id
        return next(iter(self.settings.worlds.keys()), None)

    def _selected_character_id(self) -> UUID | None:
        kind, obj_id = self._selected()
        if kind == "character":
            return obj_id
        return None

    def _on_tree_selection(self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None) -> None:
        if current is None:
            self.right.setCurrentWidget(self.global_page)
            return

        kind, obj_id = current.data(0, Qt.ItemDataRole.UserRole)
        if kind == "world" and obj_id is not None:
            self.world_editor.set_world(self.settings.worlds.get(obj_id))
            self.right.setCurrentWidget(self.world_editor)
            return

        if kind == "character" and obj_id is not None:
            self.character_editor.set_character(self.settings.characters.get(obj_id))
            self.right.setCurrentWidget(self.character_editor)
            return

        self.world_editor.set_world(None)
        self.character_editor.set_character(None)
        self.right.setCurrentWidget(self.global_page)

    def _create_world(self) -> None:
        world = World(name="New World", host=Host(address="", port=4000, tls=False))
        self.settings.worlds[world.id] = world
        save_world(world)
        self.rebuild_tree()
        self.data_changed.emit()

    def _copy_world(self) -> None:
        world_id = self._selected_world_id()
        if world_id is None:
            return
        source = self.settings.worlds.get(world_id)
        if source is None:
            return

        copy = source.model_copy(deep=True)
        copy.id = uuid4()
        copy.name = f"{source.name} (Copy)".strip()
        self.settings.worlds[copy.id] = copy
        save_world(copy)
        self.rebuild_tree()
        self.data_changed.emit()

    def _delete_world(self) -> None:
        world_id = self._selected_world_id()
        if world_id is None:
            return

        world = self.settings.worlds.get(world_id)
        if world is None:
            return

        chars = [c for c in self.settings.characters.values() if c.world_id == world_id]
        if chars:
            QMessageBox.warning(
                self,
                "Cannot Delete World",
                "Delete or rehome its characters first.",
            )
            return

        if QMessageBox.question(
            self,
            "Delete World",
            f"Delete world '{world.name}'?",
        ) != QMessageBox.StandardButton.Yes:
            return

        del self.settings.worlds[world_id]
        delete_world(world_id)
        self.rebuild_tree()
        self.data_changed.emit()

    def _connect_selected_character(self) -> None:
        char_id = self._selected_character_id()
        if char_id is None:
            QMessageBox.information(self, "Select Character", "Select a character first.")
            return
        self.connect_character_requested.emit(char_id)

    def _create_character(self) -> None:
        world_id = self._selected_world_id()
        if world_id is None:
            QMessageBox.warning(self, "No Worlds", "Create a world first.")
            return

        char = Character(world_id=world_id, name="New Character")
        self.settings.characters[char.id] = char
        save_character(char)
        self.rebuild_tree()
        self.data_changed.emit()

    def _copy_character(self) -> None:
        char_id = self._selected_character_id()
        if char_id is None:
            return

        source = self.settings.characters.get(char_id)
        if source is None:
            return

        copy = source.model_copy(deep=True)
        copy.id = uuid4()
        copy.name = f"{source.name} (Copy)".strip()
        copy.window = None
        self.settings.characters[copy.id] = copy
        save_character(copy)
        self.rebuild_tree()
        self.data_changed.emit()

    def _delete_character(self) -> None:
        char_id = self._selected_character_id()
        if char_id is None:
            return

        character = self.settings.characters.get(char_id)
        if character is None:
            return

        if char_id in self._in_use_character_ids:
            QMessageBox.warning(
                self,
                "Character In Use",
                "Close the character session before deleting.",
            )
            return

        if QMessageBox.question(
            self,
            "Delete Character",
            f"Delete character '{character.name}'?",
        ) != QMessageBox.StandardButton.Yes:
            return

        del self.settings.characters[char_id]
        delete_character(char_id)
        self.rebuild_tree()
        self.data_changed.emit()

    def _rehome_character(self, char_id: UUID, target_world_id: UUID) -> None:
        character = self.settings.characters.get(char_id)
        if character is None:
            return

        if char_id in self._in_use_character_ids:
            QMessageBox.warning(
                self,
                "Character In Use",
                "Cannot rehome a character while its session is open.",
            )
            self.character_editor.set_character(character)
            return

        character.world_id = target_world_id
        save_character(character)
        self.rebuild_tree()
        self.data_changed.emit()
