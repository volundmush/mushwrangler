from __future__ import annotations

from enum import Enum

from PySide6.QtGui import QBrush, QColor, QFont, QTextCharFormat


class _ParserState(Enum):
    NORMAL = "normal"
    ESCAPED = "escaped"
    ANSI_ESC = "ansi_esc"


class ANSIParser:
    def __init__(self) -> None:
        self._state = _ParserState.NORMAL
        self._formatter = QTextCharFormat()
        self._segment_buffer = bytearray()
        self._ansi_buffer = bytearray()

    def parse(self, data: bytes) -> list[tuple[QTextCharFormat, str]]:
        out: list[tuple[QTextCharFormat, str]] = []

        for byte in data:
            if self._state == _ParserState.NORMAL:
                if byte == 0x1B:
                    self._state = _ParserState.ESCAPED
                    self._append(out)
                else:
                    self._segment_buffer.append(byte)
                continue

            if self._state == _ParserState.ESCAPED:
                if byte == ord("["):
                    self._state = _ParserState.ANSI_ESC
                continue

            if self._state == _ParserState.ANSI_ESC:
                if byte == ord("m"):
                    self._state = _ParserState.NORMAL
                    self._apply()
                else:
                    self._ansi_buffer.append(byte)

        self._append(out)
        return out

    def _append(self, current: list[tuple[QTextCharFormat, str]]) -> None:
        if not self._segment_buffer:
            return

        current.append(
            (
                QTextCharFormat(self._formatter),
                self._segment_buffer.decode("utf-8", errors="replace"),
            )
        )
        self._segment_buffer.clear()

    @staticmethod
    def _xterm256_color(idx: int) -> QColor:
        if idx < 16:
            system_colors = [
                QColor("black"),
                QColor("red"),
                QColor("green"),
                QColor("yellow"),
                QColor("blue"),
                QColor("magenta"),
                QColor("cyan"),
                QColor("white"),
                QColor(128, 128, 128),
                QColor(255, 128, 0),
                QColor(128, 255, 0),
                QColor(255, 255, 0),
                QColor(0, 128, 255),
                QColor(255, 0, 255),
                QColor(0, 255, 255),
                QColor(255, 255, 255),
            ]
            return system_colors[idx]

        if idx < 232:
            i = idx - 16
            b = i % 6
            i //= 6
            g = i % 6
            i //= 6
            r = i % 6

            def conv(x: int) -> int:
                return 0 if x == 0 else 55 + x * 40

            return QColor(conv(r), conv(g), conv(b))

        gray = 8 + (idx - 232) * 10
        return QColor(gray, gray, gray)

    def _apply_xterm(self, code: int, mode: int) -> None:
        brush = QBrush(self._xterm256_color(code))
        if mode == 38:
            self._formatter.setForeground(brush)
        else:
            self._formatter.setBackground(brush)

    def _apply_ansi(self, code: int) -> None:
        if code == 0:
            self._formatter = QTextCharFormat()
            return

        if code == 1:
            self._formatter.setFontWeight(QFont.Weight.Bold)
            return

        if code == 4:
            self._formatter.setFontUnderline(True)
            return

        if code == 30:
            self._formatter.setForeground(QBrush(QColor("black")))
        elif code == 31:
            self._formatter.setForeground(QBrush(QColor("red")))
        elif code == 32:
            self._formatter.setForeground(QBrush(QColor("green")))
        elif code == 33:
            self._formatter.setForeground(QBrush(QColor("yellow")))
        elif code == 34:
            self._formatter.setForeground(QBrush(QColor("blue")))
        elif code == 35:
            self._formatter.setForeground(QBrush(QColor("magenta")))
        elif code == 36:
            self._formatter.setForeground(QBrush(QColor("cyan")))
        elif code == 37:
            self._formatter.setForeground(QBrush(QColor("white")))
        elif code == 39:
            self._formatter.clearForeground()
        elif code == 40:
            self._formatter.setBackground(QBrush(QColor("black")))
        elif code == 41:
            self._formatter.setBackground(QBrush(QColor("red")))
        elif code == 42:
            self._formatter.setBackground(QBrush(QColor("green")))
        elif code == 43:
            self._formatter.setBackground(QBrush(QColor("yellow")))
        elif code == 44:
            self._formatter.setBackground(QBrush(QColor("blue")))
        elif code == 45:
            self._formatter.setBackground(QBrush(QColor("magenta")))
        elif code == 46:
            self._formatter.setBackground(QBrush(QColor("cyan")))
        elif code == 47:
            self._formatter.setBackground(QBrush(QColor("white")))
        elif code == 49:
            self._formatter.clearBackground()
        elif code == 90:
            self._formatter.setForeground(QBrush(QColor(128, 128, 128)))
        elif code == 91:
            self._formatter.setForeground(QBrush(QColor(255, 0, 0)))
        elif code == 92:
            self._formatter.setForeground(QBrush(QColor(0, 255, 0)))
        elif code == 93:
            self._formatter.setForeground(QBrush(QColor(255, 255, 0)))
        elif code == 94:
            self._formatter.setForeground(QBrush(QColor(0, 0, 255)))
        elif code == 95:
            self._formatter.setForeground(QBrush(QColor(255, 0, 255)))
        elif code == 96:
            self._formatter.setForeground(QBrush(QColor(0, 255, 255)))
        elif code == 97:
            self._formatter.setForeground(QBrush(QColor(255, 255, 255)))

    def _apply_true_color(self, mode: int, rgb: list[int]) -> None:
        if len(rgb) < 3:
            return

        r = min(max(rgb[0], 0), 255)
        g = min(max(rgb[1], 0), 255)
        b = min(max(rgb[2], 0), 255)

        brush = QBrush(QColor(r, g, b))
        if mode == 38:
            self._formatter.setForeground(brush)
        else:
            self._formatter.setBackground(brush)

    def _apply(self) -> None:
        ansi_section = self._ansi_buffer.decode("ascii", errors="ignore")
        parts = ansi_section.split(";")
        self._ansi_buffer.clear()

        mode = 0
        mode2 = 0
        rgb: list[int] = []

        for part in parts:
            try:
                code = int(part)
            except ValueError:
                continue

            if mode in (38, 48):
                if mode2 == 0:
                    mode2 = code
                elif mode2 == 2:
                    rgb.append(code)
                    if len(rgb) == 3:
                        self._apply_true_color(mode, rgb)
                        mode = 0
                        mode2 = 0
                elif mode2 == 5:
                    self._apply_xterm(code, mode)
                    mode = 0
                    mode2 = 0
                continue

            if code in (38, 48):
                mode = code
            else:
                self._apply_ansi(code)

        if rgb:
            while len(rgb) < 3:
                rgb.append(0)
            self._apply_true_color(mode, rgb)
