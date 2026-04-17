from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QAbstractSocket, QNetworkProxy, QSslSocket, QTcpSocket

from mushwrangler.models import Character, World
from mushwrangler.telnet import TelnetData, parse_telnet


class ClientConnection(QObject):
    connected = Signal()
    disconnected = Signal(str)
    text_received = Signal(bytes)
    debug_received = Signal(str)

    def __init__(self, character: Character, world: World, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._character = character
        self._world = world
        self._socket: QAbstractSocket | None = None
        self._buffer = bytearray()
        self._app_buffer_size = 262_144
        self._sub_buffer_size = 262_144

    def start(self) -> None:
        if self._socket is not None:
            return

        host = self._character.host_override or self._world.host
        if host.tls:
            socket: QAbstractSocket = QSslSocket(self)
            socket.encrypted.connect(self.connected)
        else:
            socket = QTcpSocket(self)
            socket.connected.connect(self.connected)

        socket.setProxy(self._build_proxy())

        socket.readyRead.connect(self._on_ready_read)
        socket.disconnected.connect(self._on_disconnected)
        socket.errorOccurred.connect(self._on_error)

        self._socket = socket
        if host.tls:
            assert isinstance(socket, QSslSocket)
            socket.connectToHostEncrypted(host.address, host.port)
        else:
            socket.connectToHost(host.address, host.port)

    def _build_proxy(self) -> QNetworkProxy:
        proxy_settings = self._world.proxy
        proxy_type_name = proxy_settings.type
        proxy_type = {
            "NoProxy": QNetworkProxy.ProxyType.NoProxy,
            "DefaultProxy": QNetworkProxy.ProxyType.DefaultProxy,
            "Socks5Proxy": QNetworkProxy.ProxyType.Socks5Proxy,
            "HttpProxy": QNetworkProxy.ProxyType.HttpProxy,
            "HttpCachingProxy": QNetworkProxy.ProxyType.HttpCachingProxy,
            "FtpCachingProxy": QNetworkProxy.ProxyType.FtpCachingProxy,
        }.get(proxy_type_name, QNetworkProxy.ProxyType.NoProxy)

        return QNetworkProxy(
            proxy_type,
            proxy_settings.host_name,
            proxy_settings.port,
            proxy_settings.user,
            proxy_settings.password,
        )

    def is_connected(self) -> bool:
        if self._socket is None:
            return False
        return self._socket.state() == QAbstractSocket.SocketState.ConnectedState

    def send_line(self, line: str) -> None:
        if self._socket is None:
            return
        if self._socket.state() != QAbstractSocket.SocketState.ConnectedState:
            return

        payload = (line + "\r\n").encode("utf-8", errors="replace")
        self._socket.write(payload)
        self._socket.flush()

    def close(self) -> None:
        if self._socket is None:
            return

        socket = self._socket
        self._socket = None

        try:
            socket.readyRead.disconnect(self._on_ready_read)
        except (TypeError, RuntimeError):
            pass
        try:
            socket.disconnected.disconnect(self._on_disconnected)
        except (TypeError, RuntimeError):
            pass
        try:
            socket.errorOccurred.disconnect(self._on_error)
        except (TypeError, RuntimeError):
            pass

        if socket.state() != QAbstractSocket.SocketState.UnconnectedState:
            socket.disconnectFromHost()
            if socket.state() != QAbstractSocket.SocketState.UnconnectedState:
                socket.abort()

        socket.deleteLater()

    def _on_ready_read(self) -> None:
        if self._socket is None:
            return

        incoming = bytes(self._socket.readAll())
        if not incoming:
            return

        self._buffer.extend(incoming)

        while self._buffer:
            consumed, msg = parse_telnet(
                bytes(self._buffer), self._app_buffer_size, self._sub_buffer_size
            )
            if consumed == 0:
                break

            del self._buffer[:consumed]

            if isinstance(msg, TelnetData):
                if msg.data:
                    self.text_received.emit(msg.data)
            elif msg is not None:
                self.debug_received.emit(str(msg))

    def _on_disconnected(self) -> None:
        self.disconnected.emit("Connection closed")
        self.close()

    def _on_error(self, _socket_error) -> None:
        if self._socket is None:
            self.disconnected.emit("Socket error")
            return
        self.disconnected.emit(self._socket.errorString())
        self.close()
