#ifndef CONFIG_H
#define CONFIG_H

#include <optional>

#include <QUuid>
#include <QVector>
#include <QFont>
#include <QHash>

struct FontConfig {
    std::optional<QFont> input;
    std::optional<QFont> output;
};

struct TelnetConfig {
    bool enabled;
    bool nop;
    bool naws;
    bool mccp2;
    bool mccp3;
    bool mtts;
    QString mttsName;
    bool mssp;
    bool gmcp;
};

struct NetworkConfig {
    bool keepalive;
};

struct Config {
    QVector<QUuid> autoCharacters;
    std::optional<FontConfig> fonts;
    std::optional<TelnetConfig> telnetConfig;
    std::optional<NetworkConfig> networkConfig;
};

struct Proxy {
    QUuid id;
    QString name;// Global States below...
    QString host;
    qint16 port;
    QString username;
    QString password;
};

struct Host {
    QString address;
    qint16 port;
    bool tls;
};

struct World {
    QUuid id;
    QString name;
    Host host;
    std::optional<QUuid> proxyID;
    std::optional<TelnetConfig> telnetConfig;
    std::optional<NetworkConfig> networkConfig;
    std::optional<FontConfig> fonts;
};

struct AutoLogin {
    uint8_t mode;
    QString username;
    QString password;
    QString custom;
};

struct Character {
    QUuid id;
    QUuid worldID;
    QString name;
    std::optional<AutoLogin> autoLogin;
    std::optional<QUuid> proxyID;
    std::optional<TelnetConfig> telnetConfig;
    std::optional<NetworkConfig> networkConfig;
    std::optional<FontConfig> fonts;
};

struct SettingsData {
    QHash<QUuid, Proxy> proxies;
    QHash<QUuid, World> worlds;
    QHash<QUuid, Character> characters;
    Config config;
};

extern SettingsData globalSettings;

#endif // CONFIG_H
