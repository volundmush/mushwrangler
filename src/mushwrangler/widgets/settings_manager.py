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
    QListWidget,
    QListWidgetItem,
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

from mushwrangler.models import (
    Character,
    DisplayOverrides,
    FontSpec,
    GlobalSettings,
    Host,
    ProxySettings,
    TimerEntry,
    World,
)
from mushwrangler.settings import (
    SettingsData,
    delete_character,
    delete_world,
    save_character,
    save_global_settings,
    save_world,
)

CHARSETS = ["ascii", "latin-1", "utf-8", "utf-16", "cp1252"]
PROXY_TYPES = [
    "NoProxy",
    "DefaultProxy",
    "Socks5Proxy",
    "HttpProxy",
    "HttpCachingProxy",
    "FtpCachingProxy",
]


def _resolve_display(
    base_input: FontSpec,
    base_output: FontSpec,
    base_charset: str,
    override: DisplayOverrides,
) -> tuple[FontSpec, FontSpec, str]:
    return (
        override.input_text or base_input,
        override.output_text or base_output,
        override.charset or base_charset,
    )


class GlobalDisplayEditor(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._global: GlobalSettings | None = None

        layout = QFormLayout(self)

        self.in_family = QLineEdit(self)
        self.in_style = QLineEdit(self)
        self.in_size = QSpinBox(self)
        self.in_size.setRange(6, 48)

        self.out_family = QLineEdit(self)
        self.out_style = QLineEdit(self)
        self.out_size = QSpinBox(self)
        self.out_size.setRange(6, 48)

        self.charset = QComboBox(self)
        self.charset.addItems(CHARSETS)

        layout.addRow("Input Font Family", self.in_family)
        layout.addRow("Input Font Style", self.in_style)
        layout.addRow("Input Font Size", self.in_size)
        layout.addRow("Output Font Family", self.out_family)
        layout.addRow("Output Font Style", self.out_style)
        layout.addRow("Output Font Size", self.out_size)
        layout.addRow("Charset", self.charset)

        self.in_family.editingFinished.connect(self._apply)
        self.in_style.editingFinished.connect(self._apply)
        self.in_size.valueChanged.connect(lambda _v: self._apply())
        self.out_family.editingFinished.connect(self._apply)
        self.out_style.editingFinished.connect(self._apply)
        self.out_size.valueChanged.connect(lambda _v: self._apply())
        self.charset.currentIndexChanged.connect(lambda _i: self._apply())

    def set_global(self, global_settings: GlobalSettings | None) -> None:
        self._global = global_settings
        if global_settings is None:
            self.setEnabled(False)
            return

        self.setEnabled(True)
        d = global_settings.display
        self.in_family.setText(d.input_text.family)
        self.in_style.setText(d.input_text.style)
        self.in_size.setValue(d.input_text.size)
        self.out_family.setText(d.output_text.family)
        self.out_style.setText(d.output_text.style)
        self.out_size.setValue(d.output_text.size)
        idx = self.charset.findText(d.charset)
        if idx < 0:
            self.charset.addItem(d.charset)
            idx = self.charset.findText(d.charset)
        self.charset.setCurrentIndex(max(idx, 0))

    def _apply(self) -> None:
        if self._global is None:
            return
        self._global.display.input_text = FontSpec(
            family=self.in_family.text().strip(),
            style=self.in_style.text().strip() or "Normal",
            size=self.in_size.value(),
        )
        self._global.display.output_text = FontSpec(
            family=self.out_family.text().strip(),
            style=self.out_style.text().strip() or "Normal",
            size=self.out_size.value(),
        )
        self._global.display.charset = self.charset.currentText()
        save_global_settings(self._global)
        self.changed.emit()


class DisplayOverrideEditor(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._overrides: DisplayOverrides | None = None
        self._save_callback = None
        self._base_input = FontSpec()
        self._base_output = FontSpec()
        self._base_charset = "utf-8"

        layout = QFormLayout(self)

        self.enable_input = QCheckBox("Override input font", self)
        self.in_family = QLineEdit(self)
        self.in_style = QLineEdit(self)
        self.in_size = QSpinBox(self)
        self.in_size.setRange(6, 48)

        self.enable_output = QCheckBox("Override output font", self)
        self.out_family = QLineEdit(self)
        self.out_style = QLineEdit(self)
        self.out_size = QSpinBox(self)
        self.out_size.setRange(6, 48)

        self.enable_charset = QCheckBox("Override charset", self)
        self.charset = QComboBox(self)
        self.charset.addItems(CHARSETS)

        layout.addRow(self.enable_input)
        layout.addRow("Input Font Family", self.in_family)
        layout.addRow("Input Font Style", self.in_style)
        layout.addRow("Input Font Size", self.in_size)
        layout.addRow(self.enable_output)
        layout.addRow("Output Font Family", self.out_family)
        layout.addRow("Output Font Style", self.out_style)
        layout.addRow("Output Font Size", self.out_size)
        layout.addRow(self.enable_charset)
        layout.addRow("Charset", self.charset)

        for w in [
            self.enable_input,
            self.enable_output,
            self.enable_charset,
        ]:
            w.stateChanged.connect(lambda _s: self._apply())

        for w in [
            self.in_family,
            self.in_style,
            self.out_family,
            self.out_style,
        ]:
            w.editingFinished.connect(self._apply)

        self.in_size.valueChanged.connect(lambda _v: self._apply())
        self.out_size.valueChanged.connect(lambda _v: self._apply())
        self.charset.currentIndexChanged.connect(lambda _i: self._apply())

    def set_target(
        self,
        overrides: DisplayOverrides | None,
        base_input: FontSpec,
        base_output: FontSpec,
        base_charset: str,
        save_callback,
    ) -> None:
        self._overrides = overrides
        self._save_callback = save_callback
        self._base_input = base_input
        self._base_output = base_output
        self._base_charset = base_charset

        if overrides is None:
            self.setEnabled(False)
            return

        self.setEnabled(True)
        input_spec, output_spec, charset = _resolve_display(
            base_input, base_output, base_charset, overrides
        )

        self.enable_input.setChecked(overrides.input_text is not None)
        self.in_family.setText(input_spec.family)
        self.in_style.setText(input_spec.style)
        self.in_size.setValue(input_spec.size)

        self.enable_output.setChecked(overrides.output_text is not None)
        self.out_family.setText(output_spec.family)
        self.out_style.setText(output_spec.style)
        self.out_size.setValue(output_spec.size)

        self.enable_charset.setChecked(overrides.charset is not None)
        idx = self.charset.findText(charset)
        if idx < 0:
            self.charset.addItem(charset)
            idx = self.charset.findText(charset)
        self.charset.setCurrentIndex(max(idx, 0))

    def _apply(self) -> None:
        if self._overrides is None or self._save_callback is None:
            return

        if self.enable_input.isChecked():
            self._overrides.input_text = FontSpec(
                family=self.in_family.text().strip(),
                style=self.in_style.text().strip() or "Normal",
                size=self.in_size.value(),
            )
        else:
            self._overrides.input_text = None

        if self.enable_output.isChecked():
            self._overrides.output_text = FontSpec(
                family=self.out_family.text().strip(),
                style=self.out_style.text().strip() or "Normal",
                size=self.out_size.value(),
            )
        else:
            self._overrides.output_text = None

        if self.enable_charset.isChecked():
            self._overrides.charset = self.charset.currentText()
        else:
            self._overrides.charset = None

        self._save_callback()
        self.changed.emit()


class TimerEditor(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._timers: list[TimerEntry] | None = None
        self._save_callback = None

        outer = QVBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal, self)

        left = QWidget(split)
        left_layout = QVBoxLayout(left)
        self.list = QListWidget(left)
        self.list.currentRowChanged.connect(self._on_timer_selected)
        left_layout.addWidget(self.list)

        list_buttons = QHBoxLayout()
        self.add_btn = QPushButton("Add", left)
        self.del_btn = QPushButton("Delete", left)
        list_buttons.addWidget(self.add_btn)
        list_buttons.addWidget(self.del_btn)
        left_layout.addLayout(list_buttons)

        right = QWidget(split)
        right_form = QFormLayout(right)
        self.name_edit = QLineEdit(right)
        self.interval_spin = QSpinBox(right)
        self.interval_spin.setRange(100, 3_600_000)
        self.enabled_check = QCheckBox("Enabled", right)
        self.script_edit = QTextEdit(right)
        self.script_edit.setMaximumHeight(180)

        right_form.addRow("Name", self.name_edit)
        right_form.addRow("Interval (ms)", self.interval_spin)
        right_form.addRow(self.enabled_check)
        right_form.addRow("Command Script", self.script_edit)

        split.setSizes([260, 420])
        outer.addWidget(split)

        self.add_btn.clicked.connect(self._add_timer)
        self.del_btn.clicked.connect(self._delete_timer)
        self.name_edit.editingFinished.connect(self._apply_current)
        self.interval_spin.valueChanged.connect(lambda _v: self._apply_current())
        self.enabled_check.stateChanged.connect(lambda _s: self._apply_current())
        self.script_edit.textChanged.connect(self._apply_current)

    def set_target(self, timers: list[TimerEntry] | None, save_callback) -> None:
        self._timers = timers
        self._save_callback = save_callback
        self.list.blockSignals(True)
        self.list.clear()

        if timers is None:
            self.list.blockSignals(False)
            self.setEnabled(False)
            return

        self.setEnabled(True)
        for timer in timers:
            self.list.addItem(timer.name or "(unnamed timer)")
        self.list.blockSignals(False)
        if timers:
            self.list.setCurrentRow(0)
        else:
            self._show_timer(None)

    def _add_timer(self) -> None:
        if self._timers is None:
            return
        timer = TimerEntry(id=uuid4(), name="New Timer", interval_ms=5000, command_script="")
        self._timers.append(timer)
        self.list.addItem(timer.name)
        self.list.setCurrentRow(self.list.count() - 1)
        self._save()

    def _delete_timer(self) -> None:
        if self._timers is None:
            return
        row = self.list.currentRow()
        if row < 0 or row >= len(self._timers):
            return
        del self._timers[row]
        self.list.takeItem(row)
        if self._timers:
            self.list.setCurrentRow(max(0, row - 1))
        else:
            self._show_timer(None)
        self._save()

    def _on_timer_selected(self, row: int) -> None:
        if self._timers is None or row < 0 or row >= len(self._timers):
            self._show_timer(None)
            return
        self._show_timer(self._timers[row])

    def _show_timer(self, timer: TimerEntry | None) -> None:
        enabled = timer is not None
        self.name_edit.setEnabled(enabled)
        self.interval_spin.setEnabled(enabled)
        self.enabled_check.setEnabled(enabled)
        self.script_edit.setEnabled(enabled)

        self.name_edit.blockSignals(True)
        self.interval_spin.blockSignals(True)
        self.enabled_check.blockSignals(True)
        self.script_edit.blockSignals(True)

        self.name_edit.setText(timer.name if timer else "")
        self.interval_spin.setValue(timer.interval_ms if timer else 1000)
        self.enabled_check.setChecked(timer.enabled if timer else False)
        self.script_edit.setPlainText(timer.command_script if timer else "")

        self.name_edit.blockSignals(False)
        self.interval_spin.blockSignals(False)
        self.enabled_check.blockSignals(False)
        self.script_edit.blockSignals(False)

    def _apply_current(self) -> None:
        if self._timers is None:
            return
        row = self.list.currentRow()
        if row < 0 or row >= len(self._timers):
            return
        timer = self._timers[row]
        timer.name = self.name_edit.text().strip()
        timer.interval_ms = self.interval_spin.value()
        timer.enabled = self.enabled_check.isChecked()
        timer.command_script = self.script_edit.toPlainText()
        item = self.list.item(row)
        if item is not None:
            item.setText(timer.name or "(unnamed timer)")
        self._save()

    def _save(self) -> None:
        if self._save_callback is not None:
            self._save_callback()
        self.changed.emit()


class WorldConnectEditor(QWidget):
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
        self.proxy_type_combo = QComboBox(self)
        self.proxy_type_combo.addItems(PROXY_TYPES)
        self.proxy_host_edit = QLineEdit(self)
        self.proxy_port_spin = QSpinBox(self)
        self.proxy_port_spin.setRange(0, 65535)
        self.proxy_user_edit = QLineEdit(self)
        self.proxy_password_edit = QLineEdit(self)
        self.proxy_password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addRow("Name", self.name_edit)
        layout.addRow("Host", self.host_edit)
        layout.addRow("Port", self.port_spin)
        layout.addRow("TLS", self.tls_combo)
        layout.addRow("Proxy Type", self.proxy_type_combo)
        layout.addRow("Proxy Host", self.proxy_host_edit)
        layout.addRow("Proxy Port", self.proxy_port_spin)
        layout.addRow("Proxy User", self.proxy_user_edit)
        layout.addRow("Proxy Password", self.proxy_password_edit)

        self.name_edit.editingFinished.connect(self._apply)
        self.host_edit.editingFinished.connect(self._apply)
        self.port_spin.valueChanged.connect(lambda _v: self._apply())
        self.tls_combo.currentIndexChanged.connect(lambda _i: self._apply())
        self.proxy_type_combo.currentIndexChanged.connect(lambda _i: self._apply())
        self.proxy_host_edit.editingFinished.connect(self._apply)
        self.proxy_port_spin.valueChanged.connect(lambda _v: self._apply())
        self.proxy_user_edit.editingFinished.connect(self._apply)
        self.proxy_password_edit.editingFinished.connect(self._apply)

    def set_world(self, world: World | None) -> None:
        self._world = world
        if world is None:
            self.setEnabled(False)
            self.name_edit.clear()
            self.host_edit.clear()
            self.port_spin.setValue(1)
            self.tls_combo.setCurrentIndex(0)
            self.proxy_type_combo.setCurrentIndex(0)
            self.proxy_host_edit.clear()
            self.proxy_port_spin.setValue(0)
            self.proxy_user_edit.clear()
            self.proxy_password_edit.clear()
            return
        self.setEnabled(True)
        self.name_edit.setText(world.name)
        self.host_edit.setText(world.host.address)
        self.port_spin.setValue(world.host.port or 1)
        self.tls_combo.setCurrentIndex(1 if world.host.tls else 0)
        proxy_type = world.proxy.type
        idx = self.proxy_type_combo.findText(proxy_type)
        if idx < 0:
            self.proxy_type_combo.addItem(proxy_type)
            idx = self.proxy_type_combo.findText(proxy_type)
        self.proxy_type_combo.setCurrentIndex(max(idx, 0))
        self.proxy_host_edit.setText(world.proxy.host_name)
        self.proxy_port_spin.setValue(world.proxy.port)
        self.proxy_user_edit.setText(world.proxy.user)
        self.proxy_password_edit.setText(world.proxy.password)

    def _apply(self) -> None:
        if self._world is None:
            return
        self._world.name = self.name_edit.text().strip()
        self._world.host = Host(
            address=self.host_edit.text().strip(),
            port=self.port_spin.value(),
            tls=self.tls_combo.currentIndex() == 1,
        )
        self._world.proxy = ProxySettings(
            type=self.proxy_type_combo.currentText(),
            host_name=self.proxy_host_edit.text().strip(),
            port=self.proxy_port_spin.value(),
            user=self.proxy_user_edit.text(),
            password=self.proxy_password_edit.text(),
        )
        save_world(self._world)
        self.changed.emit()


class CharacterConnectEditor(QWidget):
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
        self.login_script_edit.setMaximumHeight(170)
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
            self.setEnabled(False)
            self.name_edit.clear()
            self.password_edit.clear()
            self.login_script_edit.clear()
            self.split_input_check.setChecked(False)
            self.launch_on_startup_check.setChecked(False)
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


class CategoryPane(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.categories = QListWidget(self)
        self.pages = QStackedWidget(self)
        layout.addWidget(self.categories)
        layout.addWidget(self.pages)
        layout.setContentsMargins(0, 0, 0, 0)
        self.categories.currentRowChanged.connect(self.pages.setCurrentIndex)

    def set_sections(self, sections: list[tuple[str, QWidget]]) -> None:
        self.categories.clear()
        while self.pages.count():
            widget = self.pages.widget(0)
            self.pages.removeWidget(widget)
        for name, widget in sections:
            self.categories.addItem(QListWidgetItem(name))
            self.pages.addWidget(widget)
        if sections:
            self.categories.setCurrentRow(0)


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

        self.right_pages = QStackedWidget(self)

        self.global_category = CategoryPane(self.right_pages)
        self.global_display_editor = GlobalDisplayEditor(self.global_category)
        self.global_display_editor.changed.connect(self._emit_data_changed)
        self.global_category.set_sections([("Display", self.global_display_editor)])
        self.right_pages.addWidget(self.global_category)

        self.world_category = CategoryPane(self.right_pages)
        self.world_connect_editor = WorldConnectEditor(self.world_category)
        self.world_connect_editor.changed.connect(self._refresh_tree_texts)
        self.world_display_editor = DisplayOverrideEditor(self.world_category)
        self.world_display_editor.changed.connect(self._emit_data_changed)
        self.world_timers_editor = TimerEditor(self.world_category)
        self.world_timers_editor.changed.connect(self._emit_data_changed)
        self.world_category.set_sections(
            [
                ("Connect Info", self.world_connect_editor),
                ("Display", self.world_display_editor),
                ("Timers", self.world_timers_editor),
            ]
        )
        self.right_pages.addWidget(self.world_category)

        self.character_category = CategoryPane(self.right_pages)
        self.character_connect_editor = CharacterConnectEditor(self.settings, self.character_category)
        self.character_connect_editor.changed.connect(self._refresh_tree_texts)
        self.character_connect_editor.rehome_requested.connect(self._rehome_character)
        self.character_display_editor = DisplayOverrideEditor(self.character_category)
        self.character_display_editor.changed.connect(self._emit_data_changed)
        self.character_timers_editor = TimerEditor(self.character_category)
        self.character_timers_editor.changed.connect(self._emit_data_changed)
        self.character_category.set_sections(
            [
                ("Connect Info", self.character_connect_editor),
                ("Display", self.character_display_editor),
                ("Timers", self.character_timers_editor),
            ]
        )
        self.right_pages.addWidget(self.character_category)

        self.addWidget(left)
        self.addWidget(self.right_pages)
        self.setChildrenCollapsible(False)
        self.setSizes([420, 760])

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
        self.character_connect_editor.refresh_worlds()
        self.global_display_editor.set_global(self.settings.global_settings)

    def _emit_data_changed(self) -> None:
        self.data_changed.emit()

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

        self.data_changed.emit()

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

    def _on_tree_selection(
        self,
        current: QTreeWidgetItem | None,
        _previous: QTreeWidgetItem | None,
    ) -> None:
        if current is None:
            self.right_pages.setCurrentIndex(0)
            return

        kind, obj_id = current.data(0, Qt.ItemDataRole.UserRole)
        if kind == "global":
            self.global_display_editor.set_global(self.settings.global_settings)
            self.right_pages.setCurrentWidget(self.global_category)
            return

        if kind == "world" and obj_id is not None:
            world = self.settings.worlds.get(obj_id)
            self.world_connect_editor.set_world(world)
            if world is not None:
                g = self.settings.global_settings.display
                self.world_display_editor.set_target(
                    world.display,
                    g.input_text,
                    g.output_text,
                    g.charset,
                    lambda w=world: save_world(w),
                )
                self.world_timers_editor.set_target(world.timers, lambda w=world: save_world(w))
            self.right_pages.setCurrentWidget(self.world_category)
            return

        if kind == "character" and obj_id is not None:
            character = self.settings.characters.get(obj_id)
            self.character_connect_editor.set_character(character)
            if character is not None:
                world = self.settings.worlds.get(character.world_id)
                g = self.settings.global_settings.display
                base_input = g.input_text
                base_output = g.output_text
                base_charset = g.charset
                if world is not None:
                    base_input, base_output, base_charset = _resolve_display(
                        base_input,
                        base_output,
                        base_charset,
                        world.display,
                    )
                self.character_display_editor.set_target(
                    character.display,
                    base_input,
                    base_output,
                    base_charset,
                    lambda c=character: save_character(c),
                )
                self.character_timers_editor.set_target(
                    character.timers,
                    lambda c=character: save_character(c),
                )
            self.right_pages.setCurrentWidget(self.character_category)
            return

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
            self.character_connect_editor.set_character(character)
            return

        character.world_id = target_world_id
        save_character(character)
        self.rebuild_tree()
        self.data_changed.emit()
