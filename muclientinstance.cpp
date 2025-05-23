#include <QMetaEnum>
#include "muclientinstance.h"
#include <QFontDatabase>
#include <QSplitter>
#include <QScrollBar>

MUClientInstance::MUClientInstance(Character& character, QWidget* parent) :
    character(character),
    world(globalSettings.worlds[character.worldID]),
    QSplitter(Qt::Vertical, parent) {

    editor = new QTextEdit(this);
    splitter = new QSplitter(Qt::Vertical, this);
    input2 = new QTextEdit(splitter);
    //input2->setHidden(true);
    input = new QTextEdit(splitter);
    editor->setReadOnly(true);

    QFont mono = QFontDatabase::systemFont(QFontDatabase::FixedFont);

    for(auto e : {editor, input, input2}) {
        e->setLineWrapMode(QTextEdit::WidgetWidth);
        e->setFont(mono);
    }

    for(auto e : {input, input2}) {
        e->installEventFilter(this);
    }

    splitter->setStretchFactor(0, 1);  // console takes all extra space
    splitter->setStretchFactor(1, 0);  // input stays minimal

    telnet = new TelnetProtocol(this);
    connect(telnet, &TelnetProtocol::telnetEvent,
            this, &MUClientInstance::handleTelnet);

}

bool MUClientInstance::eventFilter(QObject *watched, QEvent *ev) {
    if ((watched == input || watched == input2) && ev->type() == QEvent::KeyPress) {
        auto *in = dynamic_cast<QTextEdit*>(watched);
        auto *ke = static_cast<QKeyEvent*>(ev);
        if (ke->key() == Qt::Key_Return && ke->modifiers() == Qt::NoModifier) {
            QString text = in->toPlainText().trimmed();
            if (!text.isEmpty()) {
                sendLine(text);
                qDebug() << "Send:" << text;
                in->clear();
            }
            return true;  // eat the event so no newline is inserted
        }
    }
    return QObject::eventFilter(watched, ev);
}

std::optional<QNetworkProxy> MUClientInstance::makeProxy() {
    std::optional<QNetworkProxy> proxy;
    if(character.proxyID) {
        if(globalSettings.proxies.contains(*character.proxyID)) {
            auto p = globalSettings.proxies.value(*character.proxyID);
            // Create a networkProxy here...
        } else {
            // this is an error condition.
        }
    } else if(world.proxyID) {
        if(globalSettings.proxies.contains(*world.proxyID)) {
            auto p = globalSettings.proxies.value(*world.proxyID);
            // Create a networkProxy here...
        } else {
            // this is an error condition.
        }
    }
    return proxy;
}

void MUClientInstance::start() {

    if(sock) {
        sock->disconnect();
        sock->deleteLater();
        sock = nullptr;
    }

    auto proxy = makeProxy();

    sock = world.host.tls ? new QSslSocket(this) : new QTcpSocket(this);
    if (proxy) {
        sock->setProxy(*proxy);
    }

    // connect our signals and slots...
    connect(sock, &QTcpSocket::readyRead, this, &MUClientInstance::onSocketReadyRead);
    connect(sock, &QTcpSocket::connected, this, &MUClientInstance::onSocketConnected);
    connect(sock, &QTcpSocket::disconnected, this, &MUClientInstance::onSocketDisconnected);
    connect(sock, &QTcpSocket::errorOccurred, this, &MUClientInstance::onSocketError);

    sock->connectToHost(world.host.address, world.host.port);
}

void MUClientInstance::onSocketReadyRead()
{
    QByteArray data = sock->readAll();
    telnet->receiveData(data);
}

void MUClientInstance::handleTelnet(const TelnetEvent &ev) {
    // 1) Check the type of event
    if (std::holds_alternative<TelnetEventReceiveData>(ev)) {
        auto data = std::get<TelnetEventReceiveData>(ev).data;
        // 2) Handle the data...
        handleOutput(data);
    } else if (std::holds_alternative<TelnetEventSendData>(ev)) {
        auto data = std::get<TelnetEventSendData>(ev).data;
        // 3) Handle the data...
        sock->write(data);
    } else if (std::holds_alternative<TelnetEventOptionStateChange>(ev)) {
        auto opt = std::get<TelnetEventOptionStateChange>(ev);
        editor->append(QString("** Option %1 %2 %3 **\n")
                       .arg(opt.option)
                       .arg(opt.local ? "local" : "remote")
                       .arg(opt.state));
    } else if (std::holds_alternative<TelnetEventSubData>(ev)) {
        auto sub = std::get<TelnetEventSubData>(ev);
        editor->append(QString("** Subnegotiation %1 **\n").arg(sub.option));
    } else if (std::holds_alternative<TelnetEventCommand>(ev)) {
        auto cmd = std::get<TelnetEventCommand>(ev);
        editor->append(QString("** Command %1 **\n").arg(cmd.command));
    }
}

void MUClientInstance::handleOutput(const QByteArray& data) {
    // 1) grab the scrollbar and see if we’re already at the bottom
    auto *bar      = editor->verticalScrollBar();
    const bool wasAtBottom = (bar->value() == bar->maximum());

    auto segments = ansiparser.parse(data);

    // 2) append your ANSI‑parsed segments exactly as before
    QTextCursor cur(editor->document());
    cur.movePosition(QTextCursor::End);
    for (const auto &seg : std::as_const(segments)) {
        const auto &fmt  = std::get<0>(seg);
        const auto &text = std::get<1>(seg);
        cur.insertText(text, fmt);
    }

    // 3) only scroll if the user was already at the bottom
    if (wasAtBottom) {
        editor->setTextCursor(cur);
        editor->ensureCursorVisible();
    }
}

void MUClientInstance::sendLine(const QString& l) {
    if (sock && sock->state() == QAbstractSocket::ConnectedState) {
        auto data = QString(l); // force a copy.
        // erase all \r...
        data.remove('\r');
        // replace all \n with \r\n
        data.replace('\n', "\r\n");
        // Send and ensure a newline is sent.
        sock->write(data.toUtf8());
        if(!data.endsWith("\r\n")) sock->write("\r\n");
    }
}

void MUClientInstance::onSocketConnected() {
    editor->append("** Connected **\r\n");
}

void MUClientInstance::onSocketDisconnected() {
    editor->append("** Disconnected **\r\n");
}

void MUClientInstance::onSocketError(QAbstractSocket::SocketError err)
{
    // get the enum name
    const QMetaEnum me = QMetaEnum::fromType<QAbstractSocket::SocketError>();
    QString name = me.valueToKey(err);

    // get the detailed text
    QString text = sock->errorString();

    editor->append(QString("** Socket error: %1 (%2) **\n")
                       .arg(name, text));
}


MUClientInstance::~MUClientInstance()
{
    if (sock) {
        // sever all socket→this connections
        sock->disconnect(this);
        sock->disconnect();
    }
}
