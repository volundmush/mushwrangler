#ifndef MUSHWRANGLER_H
#define MUSHWRANGLER_H

#include <QMainWindow>
#include <QMdiArea>
#include <QMdiSubWindow>


class MUSHWrangler : public QMainWindow
{
    Q_OBJECT

public:
    MUSHWrangler(QWidget *parent = nullptr);
    ~MUSHWrangler();

    QMdiArea *mdiarea;


private:

};
#endif // MUSHWRANGLER_H
