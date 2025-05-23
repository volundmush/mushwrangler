#include "ansiparser.h"
#include <QColor>
#include <QBrush>
#include <QFont>

ANSIParser::ANSIParser() {}

QList<std::tuple<QTextCharFormat, QString>> ANSIParser::parse(const QByteArray& data) {
    QList<std::tuple<QTextCharFormat, QString>> out;

    for(auto b : data) {
        switch(st) {
            case Normal: {
            if(b == '\x1b') {
                // it's an escape..
                st = Escaped;
                append(out);
            } else {
                segbuffer.append(b);
            }
            }
            break;
            case Escaped:
                switch(b) {
                    case '[':
                        // it's an ANSI escape...
                        st = AnsiEsc;
                        break;
                    default:
                        // I don't know what this is...
                        break;
                }
            break;
            case AnsiEsc:
                if(b == 'm') {
                    st = Normal;
                    apply();
                } else {
                    ansibuffer.append(b);
                }
                break;
        }
    }

    append(out);

    // finally we're done.
    return out;
}

void ANSIParser::append(QList<std::tuple<QTextCharFormat, QString>>& current) {
    if(segbuffer.isEmpty()) return;

    current.append(std::make_tuple(formatter, segbuffer));
    segbuffer.clear();
}

// add this at the top of your .cpp if you like, or inline in applyXterm:
static QColor xterm256Color(int idx)
{
    if (idx < 16) {
        // standard system colors (you can tweak these if you like)
        static const QColor sys[16] = {
            Qt::black,    Qt::red,      Qt::green,   Qt::yellow,
            Qt::blue,     Qt::magenta,  Qt::cyan,    Qt::white,
            QColor(128,128,128), QColor(255,128,0), QColor(128,255,0), QColor(255,255,0),
            QColor(0,128,255),   QColor(255,0,255), QColor(0,255,255), QColor(255,255,255)
        };
        return sys[idx];
    }
    if (idx < 232) {
        // 6×6×6 color cube
        int i = idx - 16;
        int b = i % 6; i /= 6;
        int g = i % 6; i /= 6;
        int r = i % 6;
        auto conv = [](int x){ return x == 0 ? 0 : 55 + x*40; };
        return QColor(conv(r), conv(g), conv(b));
    }
    // grayscale ramp 232–255
    int gray = 8 + (idx - 232) * 10;
    return QColor(gray, gray, gray);
}

void ANSIParser::applyXterm(int code, int mode)
{
    // `code` is your 0–255 index, `mode` is 38 (foreground) or 48 (background)
    QColor col = xterm256Color(code);
    QBrush brush(col);

    if (mode == 38) {
        formatter.setForeground(brush);
    } else /* mode == 48 */ {
        formatter.setBackground(brush);
    }
}

void ANSIParser::applyAnsi(int code) {
    switch (code) {
    case 0:
        // reset all attributes
        formatter = QTextCharFormat();
        break;

    case 1:
        // bold
        formatter.setFontWeight(QFont::Bold);
        break;
    case 4:
        // underline
        formatter.setFontUnderline(true);
        break;

        // foreground colors 30–37
    case 30: formatter.setForeground(QBrush(Qt::black));   break;
    case 31: formatter.setForeground(QBrush(Qt::red));     break;
    case 32: formatter.setForeground(QBrush(Qt::green));   break;
    case 33: formatter.setForeground(QBrush(Qt::yellow));  break;
    case 34: formatter.setForeground(QBrush(Qt::blue));    break;
    case 35: formatter.setForeground(QBrush(Qt::magenta)); break;
    case 36: formatter.setForeground(QBrush(Qt::cyan));    break;
    case 37: formatter.setForeground(QBrush(Qt::white));   break;
    case 39:
        // default foreground
        formatter.clearForeground();
        break;

        // background colors 40–47
    case 40: formatter.setBackground(QBrush(Qt::black));   break;
    case 41: formatter.setBackground(QBrush(Qt::red));     break;
    case 42: formatter.setBackground(QBrush(Qt::green));   break;
    case 43: formatter.setBackground(QBrush(Qt::yellow));  break;
    case 44: formatter.setBackground(QBrush(Qt::blue));    break;
    case 45: formatter.setBackground(QBrush(Qt::magenta)); break;
    case 46: formatter.setBackground(QBrush(Qt::cyan));    break;
    case 47: formatter.setBackground(QBrush(Qt::white));   break;

    case 49:
        // default background
        formatter.clearBackground();
        break;

        // bright foreground 90–97
    case 90: formatter.setForeground(QBrush(QColor(128,128,128))); /*bright black*/ break;
    case 91: formatter.setForeground(QBrush(QColor(255,  0,  0))); /*bright red*/   break;
    case 92: formatter.setForeground(QBrush(QColor(  0,255,  0))); /*bright green*/ break;
    case 93: formatter.setForeground(QBrush(QColor(255,255,  0))); /*bright yellow*/break;
    case 94: formatter.setForeground(QBrush(QColor(  0,  0,255))); /*bright blue*/  break;
    case 95: formatter.setForeground(QBrush(QColor(255,  0,255))); /*bright magenta*/break;
    case 96: formatter.setForeground(QBrush(QColor(  0,255,255))); /*bright cyan*/  break;
    case 97: formatter.setForeground(QBrush(QColor(255,255,255))); /*bright white*/ break;

    default:
        // unhandled codes (e.g. 2, 3, 5) you can add as needed…
        break;
    }
}

void ANSIParser::applyTrueColor(int mode, const QList<int>& rgb)
{
    if (rgb.size() < 3) {
        return; // not enough data
    }
    // Clamp each channel to [0,255]
    int r = qBound(0, rgb[0], 255);
    int g = qBound(0, rgb[1], 255);
    int b = qBound(0, rgb[2], 255);

    QColor col(r, g, b);
    QBrush brush(col);

    if (mode == 38) {
        // 24‑bit foreground
        formatter.setForeground(brush);
    } else {
        // 48‑bit background
        formatter.setBackground(brush);
    }
}

void ANSIParser::apply() {
    QString ansisection(ansibuffer);
    auto parts = ansisection.split(";");
    ansibuffer.clear();

    int mode = 0;
    int mode2 = 0;
    QList<int> rgb;

    for(const auto &p : std::as_const(parts)) {
        bool ok = false;
        int code = p.toInt(&ok);
        if (!ok) {
            continue;
        }

        switch(mode) {
        case 38:
        case 48:
            switch(mode2) {
            case 0:
                mode2 = code;
                break;
            case 2:
                rgb.append(code);
                if(rgb.length() == 3) {
                    applyTrueColor(mode, rgb);
                    mode = 0;
                    mode2 = 0;
                }
                break;
            case 5:
                applyXterm(code, mode);
                mode = 0;
                mode2 = 0;
                break;
            }
            break;
        case 0: // normal ANSI...
        default:
            switch(code) {
            case 38:
            case 48:
                mode = code;
                break;
            default:
                applyAnsi(code);
                break;
            }
        }
    }

    if(!rgb.isEmpty()) {
        while(rgb.size() < 3) {
            rgb.append(0);
        }
        applyTrueColor(mode, rgb);
    }

}
