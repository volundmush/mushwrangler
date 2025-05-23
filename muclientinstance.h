#ifndef MUCLIENTINSTANCE_H
#define MUCLIENTINSTANCE_H

#include <QMdiSubWindow>
#include <QTextEdit>
#include <QPlainTextEdit>
#include <QSslSocket>
#include <QNetworkProxy>
#include <QSplitter>
#include <QLineEdit>
#include <QSplitter>

#include <optional>

#include "ansiparser.h"
#include "telnetprotocol.h"
#include "config.h"

class MUClientInstance : public QSplitter
{
    Q_OBJECT
public:
    MUClientInstance(Character& character, QWidget *parent = nullptr);
    ~MUClientInstance();
    QTextEdit *editor{nullptr};
    QTextEdit *input{nullptr};
    QTextEdit *input2{nullptr};
    QSplitter *splitter{nullptr};
    QTcpSocket *sock{nullptr};
    Character& character;
    World& world;
    void start();
public slots:
    void sendLine(const QString& l);
private slots:
    void onSocketReadyRead();
    void onSocketConnected();
    void onSocketDisconnected();
    void onSocketError(QAbstractSocket::SocketError err);
    void handleTelnet(const TelnetEvent &ev);
private:
    ANSIParser ansiparser;
    TelnetProtocol *telnet{nullptr};
    std::optional<QNetworkProxy> makeProxy();

    void handleOutput(const QByteArray& data);
protected:
    bool eventFilter(QObject *watched, QEvent *ev) override;

};

#endif // MUCLIENTINSTANCE_H
