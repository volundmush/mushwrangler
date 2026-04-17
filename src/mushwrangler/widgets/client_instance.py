from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QFont,
    QFontDatabase,
    QKeyEvent,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QMenu, QSplitter, QTextEdit

from mushwrangler.ansi import ANSIParser
from mushwrangler.models import Character, World
from mushwrangler.settings import save_character
from mushwrangler.transport import ClientConnection


class CommandInput(QTextEdit):
    line_submitted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._history: list[str] = []
        self._history_index: int | None = None

    def add_history(self, line: str) -> None:
        if not line:
            return
        if self._history and self._history[-1] == line:
            return
        self._history.append(line)
        self._history_index = None

    def _show_history_line(self, index: int) -> None:
        self._history_index = index
        self.setPlainText(self._history[index])
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Up:
            if not self._history:
                return

            if self._history_index is None:
                if self.toPlainText().strip("\r\n"):
                    super().keyPressEvent(event)
                    return
                self._show_history_line(len(self._history) - 1)
                return

            self._show_history_line(max(0, self._history_index - 1))
            return

        if event.key() == Qt.Key.Key_Down and self._history_index is not None:
            next_index = self._history_index + 1
            if next_index >= len(self._history):
                self._history_index = None
                self.clear()
                return
            self._show_history_line(next_index)
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._history_index = None
                super().keyPressEvent(event)
                return
            text = self.toPlainText().strip("\r\n")
            self.clear()
            self._history_index = None
            self.line_submitted.emit(text)
            return

        if self._history_index is not None:
            self._history_index = None

        super().keyPressEvent(event)


class MUClientInstance(QSplitter):
    def __init__(self, character: Character, world: World, parent=None) -> None:
        super().__init__(parent)
        self.character = character
        self.world = world
        self._ansi = ANSIParser()
        self._connection = ClientConnection(character, world, self)

        self.setOrientation(Qt.Orientation.Vertical)

        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono.setStyleHint(QFont.StyleHint.TypeWriter)

        self.output_split = QSplitter(Qt.Orientation.Vertical, self)

        self.output = QTextEdit(self.output_split)
        self.output.setReadOnly(True)
        self.output.setUndoRedoEnabled(False)
        self.output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.output.verticalScrollBar().valueChanged.connect(self._sync_tail_visibility)

        self.tail_output = QTextEdit(self.output_split)
        self.tail_output.setReadOnly(True)
        self.tail_output.setUndoRedoEnabled(False)
        self.tail_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.tail_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tail_output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tail_output.setMaximumHeight(120)

        self.output_split.setChildrenCollapsible(False)
        self.output_split.setHandleWidth(0)
        self.output_split.setSizes([1000, 0])

        self.addWidget(self.output_split)

        self.input_split = QSplitter(Qt.Orientation.Horizontal, self)
        self.input_split.setChildrenCollapsible(False)
        self.input_split.setHandleWidth(4)

        self.input = self._build_input_widget(self.input_split)
        self.input2 = self._build_input_widget(self.input_split)
        self.input2.hide()
        self.input_split.setSizes([1000, 0])
        self.addWidget(self.input_split)

        self.output.setFont(mono)
        self.tail_output.setFont(mono)
        self.input.setFont(mono)
        self.input2.setFont(mono)
        self.tail_output.hide()

        self.setChildrenCollapsible(False)
        self.setSizes([860, 160])

        self.input.line_submitted.connect(self._send_user_line)
        self.input2.line_submitted.connect(self._send_user_line)
        self._connection.connected.connect(self._on_connected)
        self._connection.disconnected.connect(self._on_disconnected)
        self._connection.text_received.connect(self._on_text_received)
        self._connection.debug_received.connect(self._on_debug_received)

        self._append_status(f"Connected profile: {world.name} / {character.name}")
        host = character.host_override or world.host
        self._append_status(
            f"Target host: {host.address}:{host.port} (tls={host.tls})"
        )
        self._set_split_input_enabled(self.character.split_input)
        self.apply_display_preferences()
        self._connection.start()

    def _build_input_widget(self, parent) -> CommandInput:
        widget = CommandInput(parent)
        widget.setAcceptRichText(False)
        widget.setPlaceholderText("Type command and press Enter (Shift+Enter for newline)")
        widget.setMaximumHeight(130)
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(
            lambda pos, w=widget: self._show_input_context_menu(w, pos)
        )
        return widget

    def _show_input_context_menu(self, widget: CommandInput, pos) -> None:
        menu = widget.createStandardContextMenu()
        menu.addSeparator()
        toggle = menu.addAction("Enable Second Input" if not self.character.split_input else "Disable Second Input")
        toggle.triggered.connect(lambda: self._toggle_split_input())
        menu.exec(widget.mapToGlobal(pos))

    def _toggle_split_input(self) -> None:
        self._set_split_input_enabled(
            not self.character.split_input,
            persist=True,
            set_focus=True,
        )

    def _set_split_input_enabled(
        self,
        enabled: bool,
        persist: bool = False,
        set_focus: bool = False,
    ) -> None:
        self.character.split_input = enabled
        if enabled:
            self.input2.show()
            self.input_split.setSizes([500, 500])
            if set_focus:
                self.input2.setFocus()
        else:
            self.input2.hide()
            self.input_split.setSizes([1000, 0])
            if set_focus:
                self.input.setFocus()

        if persist:
            save_character(self.character)

    def sync_character_preferences(self) -> None:
        self._set_split_input_enabled(self.character.split_input)
        self.apply_display_preferences()

    def apply_display_preferences(self) -> None:
        from mushwrangler.settings import load_settings

        data = load_settings()
        global_display = data.global_settings.display
        world = data.worlds.get(self.character.world_id, self.world)

        charset = global_display.charset
        in_spec = global_display.input_text
        out_spec = global_display.output_text

        if world is not None:
            if world.display.charset:
                charset = world.display.charset
            if world.display.input_text:
                in_spec = world.display.input_text
            if world.display.output_text:
                out_spec = world.display.output_text

        if self.character.display.charset:
            charset = self.character.display.charset
        if self.character.display.input_text:
            in_spec = self.character.display.input_text
        if self.character.display.output_text:
            out_spec = self.character.display.output_text

        self._ansi_charset = charset

        in_font = self.input.font()
        in_font.setFamily(in_spec.family or in_font.family())
        in_font.setPointSize(in_spec.size)

        out_font = self.output.font()
        out_font.setFamily(out_spec.family or out_font.family())
        out_font.setPointSize(out_spec.size)

        self.input.setFont(in_font)
        self.input2.setFont(in_font)
        self.output.setFont(out_font)
        self.tail_output.setFont(out_font)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._connection.close()
        super().closeEvent(event)

    def _append_status(self, text: str) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(Qt.GlobalColor.darkGray)
        self._insert_segments([(fmt, f"{text}\n")])

    def _on_connected(self) -> None:
        self._append_status("Session connected")
        script = self.character.login_script or self.character.login
        if script:
            self._send_login_script(script)

    def _on_disconnected(self, reason: str) -> None:
        self._append_status(f"Session disconnected: {reason}")

    def _on_debug_received(self, line: str) -> None:
        self._append_status(f"[telnet] {line}")

    def _on_text_received(self, data: bytes) -> None:
        if hasattr(self, "_ansi_charset") and self._ansi_charset.lower() != "utf-8":
            try:
                data = data.decode(self._ansi_charset, errors="replace").encode("utf-8")
            except LookupError:
                pass
        segments = self._ansi.parse(data)
        self._insert_segments(segments)

    def _insert_segments(self, segments: list[tuple[QTextCharFormat, str]]) -> None:
        if not segments:
            return

        out_scroll = self.output.verticalScrollBar()
        at_bottom = out_scroll.value() >= out_scroll.maximum() - 2
        old_pos = out_scroll.value()

        out_cursor = self.output.textCursor()
        out_cursor.movePosition(QTextCursor.MoveOperation.End)
        tail_cursor = self.tail_output.textCursor()
        tail_cursor.movePosition(QTextCursor.MoveOperation.End)

        for fmt, text in segments:
            out_cursor.insertText(text, fmt)
            tail_cursor.insertText(text, fmt)

        self.output.setTextCursor(out_cursor)
        self.tail_output.setTextCursor(tail_cursor)
        self.tail_output.ensureCursorVisible()

        if at_bottom:
            out_scroll.setValue(out_scroll.maximum())
        else:
            out_scroll.setValue(old_pos)

        self._trim_tail()
        self._sync_tail_visibility()

    def _trim_tail(self) -> None:
        max_blocks = 250
        doc = self.tail_output.document()
        extra = doc.blockCount() - max_blocks
        if extra <= 0:
            return

        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(extra):
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def _sync_tail_visibility(self) -> None:
        scroll = self.output.verticalScrollBar()
        at_bottom = scroll.value() >= scroll.maximum() - 2
        if at_bottom:
            self.output_split.setHandleWidth(0)
            self.tail_output.hide()
            self.output_split.setSizes([1000, 0])
            return

        self.tail_output.show()
        self.output_split.setHandleWidth(4)
        self.output_split.setSizes([880, 120])

    def _send_user_line(self, text: str) -> None:
        if not text:
            return
        if not self._connection.is_connected():
            self._append_status("Not connected; command not sent")
            return
        self.input.add_history(text)
        self.input2.add_history(text)
        self._connection.send_line(text)

    def _send_login_script(self, script: str) -> None:
        name = self.character.name
        password = self.character.password
        for line in script.splitlines():
            expanded = line.replace("%NAME%", name).replace("%PASSWORD%", password)
            command = expanded.strip("\r\n")
            if not command:
                continue
            self._send_user_line(command)
