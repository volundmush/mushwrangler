#include "settingsmanager.h"
#include "config.h"

AbstractConfigWidget::AbstractConfigWidget(QWidget *parent) : QTabWidget(parent) {}

void AbstractConfigWidget::saveConfig() {

}

GlobalConfigWidget::GlobalConfigWidget(QWidget *parent) : AbstractConfigWidget(parent) {}

WorldConfigWidget::WorldConfigWidget(QUuid uuid, QWidget *parent) : AbstractConfigWidget(parent), uuid(uuid) {}

CharacterConfigWidget::CharacterConfigWidget(QUuid uuid, QWidget *parent) : AbstractConfigWidget(parent), uuid(uuid) {}

SettingsManager::SettingsManager(QWidget *parent) : QSplitter(Qt::Horizontal, parent){
    // LEFT SIDE: A tree view of things that have settings.
    // root: Global settings. depth 1: Worlds, depth 2: Characters.
    // Right clicking on nodes allows creating/deleting/renaming things.

    // RIGHT SIDE: Changes between Global, World, and Character mode depending on selected
    // node. Each may have its own display types.

    // create left side widget.
    tree = new QTreeWidget(this);
    tree->setHeaderLabel("Settings, Worlds, Characters");

    // Create right side widget...
    // the right side will need to be swapped out between different widgets... how do we do this?
    right = new QStackedWidget(this);
    gcw = new GlobalConfigWidget(right);
    right->addWidget(gcw);

    auto wu = QUuid();
    settingsWidgets[wu] = gcw;

    auto gtwid = new QTreeWidgetItem(tree);
    gtwid->setText(0, "Global Settings");
    gtwid->setIcon(0, QIcon::fromTheme("preferences-system"));
    gtwid->setData(0, Qt::UserRole, wu);
    twids[wu] = gtwid;
    tree->addTopLevelItem(gtwid);

    worldIcon = style()->standardIcon(QStyle::SP_DriveNetIcon);
    charIcon = style()->standardIcon(QStyle::SP_FileIcon);

    for(const auto& w: std::as_const(globalSettings.worlds)) {
        createWorldNode(w.id);
    }

    for(const auto &c : std::as_const(globalSettings.characters)) {
        createCharacterNode(c.id);
    }

    gtwid->setExpanded(true);
}

void SettingsManager::createWorldNode(QUuid worldID) {
    auto &w = globalSettings.worlds[worldID];

    auto wid = new WorldConfigWidget(worldID, right);
    settingsWidgets[worldID] = wid;
    right->addWidget(wid);

    auto wu = QUuid();
    auto gtwid = twids[wu];
    auto twid = new QTreeWidgetItem(gtwid);
    twid->setText(0, w.name);
    twid->setIcon(0, worldIcon);
    twid->setData(0, Qt::UserRole, worldID);
    twids[worldID] = twid;
    gtwid->addChild(twid);
}

void SettingsManager::createCharacterNode(QUuid characterID) {
    auto &c = globalSettings.characters[characterID];
    auto worldID = c.worldID;
    auto &w = globalSettings.worlds[worldID];

    auto wid = new CharacterConfigWidget(characterID, right);
    settingsWidgets[characterID] = wid;
    right->addWidget(wid);

    auto wwid = twids[worldID];
    auto twid = new QTreeWidgetItem(wwid);
    twid->addChild(twid);
    twid->setText(0, c.name);
    twid->setIcon(0, charIcon);
    twid->setData(0, Qt::UserRole, characterID);
    twids[characterID] = twid;
}

void SettingsManager::onTreeItemChanged(QTreeWidgetItem *current, QTreeWidgetItem *previous) {
    if(previous) {
        // save the previous settings...
        auto u = current->data(0, Qt::UserRole).value<QUuid>();
        auto w = settingsWidgets[u];
        w->saveConfig();
    }
    if(previous == current) {
        return;
    }
    if(current) {
        // retrieve the UUID from the item.
        auto u = current->data(0, Qt::UserRole).value<QUuid>();
        // alter the current display...
        right->setCurrentWidget(settingsWidgets[u]);
    }
}
