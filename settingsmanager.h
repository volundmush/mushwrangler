#ifndef SETTINGSMANAGER_H
#define SETTINGSMANAGER_H

#include <QSplitter>
#include <QTreeWidget>
#include <QStackedWidget>
#include <QHash>
#include <QUuid>
#include <QTabWidget>

class AbstractConfigWidget : public QTabWidget {
    Q_OBJECT
public:
    AbstractConfigWidget(QWidget *parent = nullptr);
    virtual void saveConfig();
};

class GlobalConfigWidget : public AbstractConfigWidget {
    Q_OBJECT
public:
    GlobalConfigWidget(QWidget *parent = nullptr);
};

class WorldConfigWidget : public AbstractConfigWidget {
    Q_OBJECT
public:
    WorldConfigWidget(QUuid uuid, QWidget *parent = nullptr);
private:
    QUuid uuid;
};

class CharacterConfigWidget : public AbstractConfigWidget {
    Q_OBJECT
public:
    CharacterConfigWidget(QUuid uuid, QWidget *parent = nullptr);
private:
    QUuid uuid;
};

class SettingsManager : public QSplitter
{
    Q_OBJECT
public:
    SettingsManager(QWidget *parent = nullptr);
    void createWorld(const QString& name);
    void createCharacter(QUuid worldID, const QString& name);
private:
    QTreeWidget *tree{nullptr};
    QHash<QUuid, QTreeWidgetItem*> twids;
    QStackedWidget *right{nullptr};
    QHash<QUuid, AbstractConfigWidget*> settingsWidgets;
    GlobalConfigWidget *gcw{nullptr};
    QIcon worldIcon;
    QIcon charIcon;

    void createWorldNode(QUuid worldID);
    void createCharacterNode(QUuid characterID);
private slots:
    void onTreeItemChanged(QTreeWidgetItem *current, QTreeWidgetItem *previous);
};

#endif // SETTINGSMANAGER_H
