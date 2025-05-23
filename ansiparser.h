#ifndef ANSIPARSER_H
#define ANSIPARSER_H

#include <QByteArray>
#include <QTextCharFormat>
#include <QList>
#include <QString>
#include <tuple>


class ANSIParser
{
public:
    ANSIParser();
    QList<std::tuple<QTextCharFormat, QString>> parse(const QByteArray& data);
private:
    enum State {Normal, Escaped, AnsiEsc};
    State st = Normal;
    // Stores ANSI codes separated by ;.
    QByteArray ansibuffer;
    // The current word buffer.
    QByteArray segbuffer;
    // The current formatter.
    QTextCharFormat formatter;

    void append(QList<std::tuple<QTextCharFormat, QString>>& current);
    void apply();
    void applyAnsi(int code);
    void applyXterm(int code, int mode);
    void applyTrueColor(int mode, const QList<int>& rgb);
};

#endif // ANSIPARSER_H
