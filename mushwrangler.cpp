

#include "mushwrangler.h"
#include "muclientinstance.h"
#include "settingsmanager.h"

MUSHWrangler::MUSHWrangler(QWidget *parent) : QMainWindow(parent)
{

    auto wu = QUuid::createUuid();
    auto &w = globalSettings.worlds[wu];
    w.id = wu;
    w.name = "Convergence MUSH";
    w.host.address = "convergence.mushhaven.com";
    w.host.port = 10000;

    auto cu = QUuid::createUuid();
    auto &c = globalSettings.characters[cu];
    c.id = cu;
    c.worldID = wu;
    c.name = "Volund";

    this->setObjectName("mainwindow");
    this->mdiarea = new QMdiArea(this);
    setCentralWidget(mdiarea);
    auto sub = new QMdiSubWindow(mdiarea);
    auto client = new MUClientInstance(c, sub);
    sub->setWidget(client);
    sub->setWindowTitle(QString("%1 - %2").arg(w.name, c.name));
    mdiarea->addSubWindow(sub);
    client->start();

    auto sub2 = new QMdiSubWindow(mdiarea);
    auto set = new SettingsManager(sub2);
    sub2->setWidget(set);
    sub2->setWindowTitle("Settings");

    mdiarea->addSubWindow(sub2);
}

MUSHWrangler::~MUSHWrangler()
{

}
