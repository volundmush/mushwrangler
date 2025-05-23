#ifndef TELNETPROTOCOL_H
#define TELNETPROTOCOL_H

#include <QObject>
#include <QHash>
#include <variant>

namespace tc {
    // “NUL” is the Telnet name for code 0 (we avoid the C NULL macro)
    constexpr char NUL         = 0;
    constexpr char SGA         = 3;
    constexpr char BEL         = 7;
    constexpr char LF          = 10;
    constexpr char CR          = 13;

    // MTTS – terminal type
    constexpr char MTTS        = 24;

    constexpr char TELOPT_EOR  = 25;

    // NAWS: Negotiate About Window Size
    constexpr char NAWS        = 31;
    constexpr char LINEMODE    = 34;

    // Negotiate about charset in use.
    constexpr char CHARSET     = 42;

    // MNES: Mud New – Environ standard
    constexpr char MNES        = 39;

    // MSDP – Mud Server Data Protocol
    constexpr char MSDP        = 69;

    // Mud Server Status Protocol
    constexpr char MSSP        = 70;

    // Compression
    // MCCP1 (85) is deprecated
    constexpr char MCCP2       = 86;
    constexpr char MCCP3       = 87;

    // MUD eXtension Protocol
    constexpr char MXP         = 91;

    // GMCP – Generic MUD Communication Protocol
    constexpr char GMCP        = 201;

    constexpr char EOR         = 239;
    constexpr char SE          = 240;
    constexpr char NOP         = 241;
    constexpr char GA          = 249;

    constexpr char SB          = 250;
    constexpr char WILL        = 251;
    constexpr char WONT        = 252;
    constexpr char DO          = 253;
    constexpr char DONT        = 254;

    constexpr char IAC         = 255;

}

struct TelnetEventReceiveData {
    QByteArray data;
};

struct TelnetEventSendData {
    QByteArray data;
};

struct TelnetEventOptionStateChange {
    uint8_t option;
    bool local;
    uint8_t state;
};

struct TelnetEventSubData {
    uint8_t option;
    QByteArray data;
};

struct TelnetEventCommand {
    uint8_t command;
};

using TelnetEvent = std::variant<TelnetEventReceiveData,
                                 TelnetEventSendData,
                                 TelnetEventOptionStateChange,
                                 TelnetEventSubData,
                                 TelnetEventCommand
                                 >;

Q_DECLARE_METATYPE(TelnetEvent)

struct TelnetOptionState {
    uint8_t status;
    bool start;
    bool support;
};

struct TelnetOptionPerspective {
    TelnetOptionState local;
    TelnetOptionState remote;
};

class TelnetProtocol : public QObject
{
    Q_OBJECT
public:
    explicit TelnetProtocol(QObject *parent = nullptr);
public slots:
    void receiveData(const QByteArray &data);
private:
    QByteArray inBuffer;
    QHash<char, TelnetOptionPerspective> options;
    void receiveNegotiate(char premise, char option);
signals:
    void telnetEvent(const TelnetEvent &ev);
};

#endif // TELNETPROTOCOL_H
