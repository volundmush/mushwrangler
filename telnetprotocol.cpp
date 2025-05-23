#include "telnetprotocol.h"

TelnetProtocol::TelnetProtocol(QObject *parent)
    : QObject{parent}
{


}

void TelnetProtocol::receiveData(const QByteArray &data)
{
    inBuffer.append(data);

    while (!inBuffer.isEmpty()) {
        if(inBuffer.at(0) == tc::IAC) {
            auto avail = inBuffer.size();
            if(avail < 2) {
                // need at least 2 bytes to do something with an IAC...
                return;
            }
            auto sec = inBuffer.at(1);
            switch(sec) {
                case tc::IAC: {
                    // it's a literal byte 255.
                    inBuffer.remove(0, 2);
                    TelnetEventReceiveData ev;
                    ev.data.append(tc::IAC);
                    emit telnetEvent(ev);
                    }
                    break;
                case tc::SB: {
                    // subnegotiation... need to find the end...
                    if(avail < 5) {
                        // we need at least a IAC SB <option> <bytes> IAC SE here...
                        return;
                    }
                    }
                    break;
                case tc::WILL:
                case tc::WONT:
                case tc::DO:
                case tc::DONT: {
                    if(avail < 3) return;
                    auto op = inBuffer.at(2);
                    inBuffer.remove(0, 3);
                    receiveNegotiate(sec, op);
                }
                break;
                default: {
                    // it's some kind of command.
                    TelnetEventCommand cmd;
                    cmd.command = sec;
                    inBuffer.remove(0, 2);
                    emit telnetEvent(cmd);
                }
                break;
            }
        } else {
            // seek out a tc::IAC... it might not exist...
            // if it doesn't, we can just send the data
            // as-is.
            TelnetEventReceiveData ev;
            auto idx = inBuffer.indexOf(tc::IAC);
            if(idx == -1) {
                ev.data = inBuffer;
                inBuffer.clear();
                emit telnetEvent(ev);
                return;
            } else {
                ev.data = inBuffer.left(idx);
                inBuffer.remove(0, idx);
                emit telnetEvent(ev);
            }
        }

    }

}

void TelnetProtocol::receiveNegotiate(char premise, char option) {

}
