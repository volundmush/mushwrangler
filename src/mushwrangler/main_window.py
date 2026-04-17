from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import QMainWindow, QMdiArea, QMdiSubWindow, QStatusBar, QToolBar

from mushwrangler.models import Character, WindowState
from mushwrangler.settings import SettingsData, save_character
from mushwrangler.widgets.client_instance import MUClientInstance
from mushwrangler.widgets.settings_manager import SettingsManager


class _SessionSubWindow(QMdiSubWindow):
    geometry_changed = Signal()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self.geometry_changed.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.geometry_changed.emit()

    def closeEvent(self, event) -> None:
        self.geometry_changed.emit()
        super().closeEvent(event)


class MUSHWranglerWindow(QMainWindow):
    def __init__(self, settings: SettingsData, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._session_actions: dict[QMdiSubWindow, QAction] = {}
        self._character_menu_actions: dict[UUID, QAction] = {}
        self._session_windows_by_character: dict[UUID, QMdiSubWindow] = {}
        self._settings_widget: SettingsManager | None = None
        self._settings_subwindow: QMdiSubWindow | None = None
        self._shutting_down = False

        self.setObjectName("mainwindow")
        self.setWindowTitle("MUSHWrangler")
        self.resize(1280, 800)

        self.mdi_area = QMdiArea(self)
        self.mdi_area.setViewMode(QMdiArea.ViewMode.SubWindowView)
        self.mdi_area.setOption(QMdiArea.AreaOption.DontMaximizeSubWindowOnActivation, True)
        self.mdi_area.subWindowActivated.connect(self._on_subwindow_activated)
        self.setCentralWidget(self.mdi_area)

        self._build_menu_bar()
        self._build_toolbars()
        self._build_status_bar()
        self._add_seed_windows()

    def _add_seed_windows(self) -> None:
        if not self.settings.characters:
            self.show_settings_window()

        startup_windows: list[QMdiSubWindow] = []
        for character in self.settings.characters.values():
            if not character.launch_on_startup:
                continue
            startup_windows.append(self._open_character_session(character))

        self._layout_new_session_windows(
            [w for w in startup_windows if w is not None and not self._has_saved_window_state(w)]
        )

        self._refresh_in_use_characters()
        self._refresh_character_menu()

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        edit_menu = self.menuBar().addMenu("&Edit")
        view_menu = self.menuBar().addMenu("&View")
        launch_menu = self.menuBar().addMenu("&Launch")
        session_menu = self.menuBar().addMenu("&Session")
        help_menu = self.menuBar().addMenu("&Help")

        self._character_menu = launch_menu.addMenu("Characters")

        tile_action = QAction("Tile Sessions", self)
        tile_action.triggered.connect(self.mdi_area.tileSubWindows)
        cascade_action = QAction("Cascade Sessions", self)
        cascade_action.triggered.connect(self.mdi_area.cascadeSubWindows)
        normalize_action = QAction("Bring Windows On Canvas", self)
        normalize_action.triggered.connect(self._normalize_subwindow_positions)

        view_menu.addAction(tile_action)
        view_menu.addAction(cascade_action)
        view_menu.addSeparator()
        view_menu.addAction(normalize_action)

        close_active_action = QAction("Close Active Session", self)
        close_active_action.triggered.connect(self._close_active_subwindow)
        session_menu.addAction(close_active_action)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings_window)

        file_menu.addAction("Quit", self.close)
        edit_menu.addAction(settings_action)
        help_menu.addAction("About")

    def _build_toolbars(self) -> None:
        main_toolbar = QToolBar("Main", self)
        main_toolbar.setObjectName("main_toolbar")
        main_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, main_toolbar)

        tile_action = QAction("Tile", self)
        tile_action.triggered.connect(self.mdi_area.tileSubWindows)
        cascade_action = QAction("Cascade", self)
        cascade_action.triggered.connect(self.mdi_area.cascadeSubWindows)
        normalize_action = QAction("Bring On Canvas", self)
        normalize_action.triggered.connect(self._normalize_subwindow_positions)

        main_toolbar.addAction(tile_action)
        main_toolbar.addAction(cascade_action)
        main_toolbar.addAction(normalize_action)

        self.session_toolbar = QToolBar("Sessions", self)
        self.session_toolbar.setObjectName("sessions_toolbar")
        self.session_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.session_toolbar)

    def _build_status_bar(self) -> None:
        status = QStatusBar(self)
        status.showMessage("Ready")
        self.setStatusBar(status)

    def _open_character_session(self, character: Character) -> QMdiSubWindow:
        existing = self._session_windows_by_character.get(character.id)
        if existing is not None and existing in self.mdi_area.subWindowList():
            self._activate_subwindow(existing)
            return existing

        world = self.settings.worlds[character.world_id]
        client = MUClientInstance(character, world, self)

        sub = _SessionSubWindow(self.mdi_area)
        sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        sub.setWidget(client)
        sub.setWindowTitle(f"{world.name} - {character.name}")
        self.mdi_area.addSubWindow(sub)
        area = self.mdi_area.viewport().rect()
        if character.window is None:
            width = max(int(area.width() * 0.58), 760)
            height = max(int(area.height() * 0.62), 460)
            sub.resize(width, height)
        else:
            sub.setGeometry(
                character.window.x,
                character.window.y,
                max(character.window.width, 300),
                max(character.window.height, 220),
            )
        sub.show()

        action = QAction(character.name, self)
        action.setCheckable(True)
        action.triggered.connect(lambda checked=False, window=sub: self._activate_subwindow(window))
        self.session_toolbar.addAction(action)
        self._session_actions[sub] = action
        self._session_windows_by_character[character.id] = sub

        sub.geometry_changed.connect(
            lambda char_id=character.id, window=sub: self._store_character_window_state(
                char_id, window
            )
        )

        sub.destroyed.connect(
            lambda _=None, char_id=character.id: self._on_session_window_destroyed(char_id)
        )
        self._normalize_subwindow_positions()
        self._refresh_in_use_characters()
        self._refresh_character_menu()
        return sub

    def _on_session_window_destroyed(self, character_id: UUID) -> None:
        window = self._session_windows_by_character.pop(character_id, None)
        if window is not None:
            action = self._session_actions.pop(window, None)
            if action is not None:
                if not self._shutting_down:
                    try:
                        self.session_toolbar.removeAction(action)
                    except RuntimeError:
                        pass
                action.deleteLater()

        if self._shutting_down:
            return

        self._refresh_in_use_characters()
        self._refresh_character_menu()

    def _layout_new_session_windows(self, windows: list[QMdiSubWindow]) -> None:
        if not windows:
            return

        area = self.mdi_area.viewport().rect()
        step_x = 34
        step_y = 30
        start_x = area.left() + 14
        start_y = area.top() + 14

        for idx, window in enumerate(windows):
            geo = window.geometry()
            x = start_x + idx * step_x
            y = start_y + idx * step_y

            max_x = max(area.right() - geo.width() + 1, area.left())
            max_y = max(area.bottom() - geo.height() + 1, area.top())

            x = min(max(x, area.left()), max_x)
            y = min(max(y, area.top()), max_y)
            window.move(x, y)

    def _activate_subwindow(self, window: QMdiSubWindow) -> None:
        if window not in self.mdi_area.subWindowList():
            return
        window.showNormal()
        self.mdi_area.setActiveSubWindow(window)
        window.raise_()
        self._ensure_window_on_canvas(window)

    def _on_subwindow_activated(self, active: QMdiSubWindow | None) -> None:
        for window, action in list(self._session_actions.items()):
            action.setChecked(window is active)

    def _close_active_subwindow(self) -> None:
        active = self.mdi_area.activeSubWindow()
        if active is None:
            return
        active.close()

    def _normalize_subwindow_positions(self) -> None:
        for window in self.mdi_area.subWindowList():
            self._ensure_window_on_canvas(window)

    def _store_character_window_state(self, character_id: UUID, window: QMdiSubWindow) -> None:
        character = self.settings.characters.get(character_id)
        if character is None:
            return
        try:
            geo = window.geometry()
        except RuntimeError:
            return
        character.window = WindowState(
            x=geo.x(),
            y=geo.y(),
            width=geo.width(),
            height=geo.height(),
        )
        save_character(character)

    def _persist_all_session_geometries(self) -> None:
        for character_id, window in list(self._session_windows_by_character.items()):
            self._store_character_window_state(character_id, window)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._shutting_down = True
        self._persist_all_session_geometries()
        super().closeEvent(event)

    def _has_saved_window_state(self, window: QMdiSubWindow) -> bool:
        for character_id, session_window in self._session_windows_by_character.items():
            if session_window is not window:
                continue
            character = self.settings.characters.get(character_id)
            return character is not None and character.window is not None
        return False

    def _refresh_in_use_characters(self) -> None:
        if self._settings_widget is None:
            return

        in_use: set[UUID] = set()
        windows = set(self.mdi_area.subWindowList())
        for character_id, sub in self._session_windows_by_character.items():
            if sub in windows:
                in_use.add(character_id)

        try:
            self._settings_widget.set_in_use_characters(in_use)
        except RuntimeError:
            self._settings_widget = None

    def _refresh_character_menu(self) -> None:
        try:
            self._character_menu.clear()
        except RuntimeError:
            return
        self._character_menu_actions.clear()

        characters = list(self.settings.characters.values())
        if not characters:
            action = QAction("No characters", self)
            action.setEnabled(False)
            self._character_menu.addAction(action)
            return

        for character in sorted(characters, key=lambda c: c.name.lower()):
            world = self.settings.worlds.get(character.world_id)
            label = character.name
            if world is not None:
                label = f"{character.name} ({world.name})"
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked=False, char_id=character.id: self._connect_character_by_id(
                    char_id
                )
            )
            self._character_menu.addAction(action)
            self._character_menu_actions[character.id] = action

    def _connect_character_by_id(self, character_id: UUID) -> None:
        character = self.settings.characters.get(character_id)
        if character is None:
            return
        self._open_character_session(character)

    def show_settings_window(self) -> None:
        if self._settings_subwindow is not None and self._settings_subwindow in self.mdi_area.subWindowList():
            self._activate_subwindow(self._settings_subwindow)
            return

        settings_widget = SettingsManager(self.settings, self)
        settings_widget.connect_character_requested.connect(self._connect_character_by_id)
        settings_widget.data_changed.connect(self._on_settings_data_changed)
        self._settings_widget = settings_widget

        settings_sub = QMdiSubWindow(self.mdi_area)
        settings_sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        settings_sub.setWidget(settings_widget)
        settings_sub.setWindowTitle("Settings")
        self.mdi_area.addSubWindow(settings_sub)
        settings_sub.resize(700, 620)
        settings_sub.move(80, 80)
        settings_sub.show()

        self._settings_subwindow = settings_sub
        settings_sub.destroyed.connect(self._on_settings_window_destroyed)
        self._refresh_in_use_characters()

    def _on_settings_window_destroyed(self, *_args) -> None:
        self._settings_subwindow = None
        self._settings_widget = None

    def _on_settings_data_changed(self) -> None:
        stale_ids = [cid for cid in self._session_windows_by_character if cid not in self.settings.characters]
        for char_id in stale_ids:
            window = self._session_windows_by_character.get(char_id)
            if window is not None and window in self.mdi_area.subWindowList():
                window.close()

        for char_id, window in self._session_windows_by_character.items():
            if window not in self.mdi_area.subWindowList():
                continue
            client = window.widget()
            if isinstance(client, MUClientInstance):
                client.sync_character_preferences()

        self._refresh_character_menu()
        self._refresh_in_use_characters()

    def _ensure_window_on_canvas(self, window: QMdiSubWindow) -> None:
        area = self.mdi_area.viewport().rect()
        geo = window.geometry()

        min_visible = 64
        max_left = max(area.right() - min_visible, area.left())
        max_top = max(area.bottom() - min_visible, area.top())

        new_x = min(max(geo.x(), area.left()), max_left)
        new_y = min(max(geo.y(), area.top()), max_top)

        max_width = max(area.width(), min_visible)
        max_height = max(area.height(), min_visible)
        new_w = min(max(geo.width(), min_visible), max_width)
        new_h = min(max(geo.height(), min_visible), max_height)

        if (new_x, new_y, new_w, new_h) != (geo.x(), geo.y(), geo.width(), geo.height()):
            window.setGeometry(new_x, new_y, new_w, new_h)
