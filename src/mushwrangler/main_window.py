from __future__ import annotations

from uuid import UUID

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QMdiArea, QMdiSubWindow, QStatusBar, QToolBar

from mushwrangler.models import Character, WindowState
from mushwrangler.settings import SettingsData, save_character
from mushwrangler.widgets.client_instance import MUClientInstance
from mushwrangler.widgets.settings_manager import SettingsManager


class _SessionWindowEventFilter(QObject):
    def __init__(
        self,
        owner: "MUSHWranglerWindow",
        character_id: UUID,
        window: QMdiSubWindow,
    ) -> None:
        super().__init__(owner)
        self._owner = owner
        self._character_id = character_id
        self._window = window

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._window and event.type() in (
            QEvent.Type.Move,
            QEvent.Type.Resize,
            QEvent.Type.Close,
        ):
            self._owner._store_character_window_state(self._character_id, self._window)
        return super().eventFilter(watched, event)


class MUSHWranglerWindow(QMainWindow):
    def __init__(self, settings: SettingsData, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._session_actions: dict[QMdiSubWindow, QAction] = {}
        self._session_windows_by_character: dict[UUID, QMdiSubWindow] = {}
        self._session_filters: dict[QMdiSubWindow, _SessionWindowEventFilter] = {}

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
        session_windows: list[QMdiSubWindow] = []
        for character in self.settings.characters.values():
            session_windows.append(self._open_character_session(character))

        settings_widget = SettingsManager(self.settings, self)
        settings_sub = QMdiSubWindow(self.mdi_area)
        settings_sub.setWidget(settings_widget)
        settings_sub.setWindowTitle("Settings")
        self.mdi_area.addSubWindow(settings_sub)
        settings_sub.resize(520, 560)
        settings_sub.move(80, 80)
        settings_sub.show()
        self._layout_new_session_windows(
            [w for w in session_windows if w is not None and not self._has_saved_window_state(w)]
        )

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        edit_menu = self.menuBar().addMenu("&Edit")
        view_menu = self.menuBar().addMenu("&View")
        session_menu = self.menuBar().addMenu("&Session")
        help_menu = self.menuBar().addMenu("&Help")

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

        file_menu.addAction("Quit", self.close)
        edit_menu.addAction("Preferences")
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

        sub = QMdiSubWindow(self.mdi_area)
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

        filt = _SessionWindowEventFilter(self, character.id, sub)
        sub.installEventFilter(filt)
        self._session_filters[sub] = filt

        sub.destroyed.connect(
            lambda _=None, window=sub, char_id=character.id: self._on_session_window_destroyed(
                window, char_id
            )
        )
        self._normalize_subwindow_positions()
        return sub

    def _on_session_window_destroyed(
        self,
        window: QMdiSubWindow,
        character_id: UUID,
    ) -> None:
        self._remove_session_action(window)
        if self._session_windows_by_character.get(character_id) is window:
            del self._session_windows_by_character[character_id]
        filt = self._session_filters.pop(window, None)
        if filt is not None:
            filt.deleteLater()

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

    def _remove_session_action(self, window: QMdiSubWindow) -> None:
        action = self._session_actions.pop(window, None)
        if action is None:
            return
        self.session_toolbar.removeAction(action)
        action.deleteLater()

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
        geo = window.geometry()
        character.window = WindowState(
            x=geo.x(),
            y=geo.y(),
            width=geo.width(),
            height=geo.height(),
        )
        save_character(character)

    def _has_saved_window_state(self, window: QMdiSubWindow) -> bool:
        for character_id, session_window in self._session_windows_by_character.items():
            if session_window is not window:
                continue
            character = self.settings.characters.get(character_id)
            return character is not None and character.window is not None
        return False

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
