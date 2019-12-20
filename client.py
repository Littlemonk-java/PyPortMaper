#-*- coding:utf-8 -*-
import socket
import threading
import json
import time

serveraddr = ("180.76.160.195", 6000)
# serveraddr = ("127.0.0.1", 6000)
maxchannel = 0
sockmap = {} #信道对应的连接

socket.setdefaulttimeout(1)

class ClientTransfer(threading.Thread):
    def __init__(self, sock):
        threading.Thread.__init__(self)
        self.sock = sock
        self.status = 0

    def run(self):
        global maxchannel

        msg = ''
        data = ''

        while True:
            try:
                data = self.sock.recv(4096)

                if data == None or len(data) < 1:
                    self.status = 1
                    return

                print data
            except BaseException,e:
                if "timed out" not in e:
                    self.status = 1
                    return
                continue

            try:
                msg = json.loads(data)
            except BaseException:
                continue

            if 'msg' not in msg:
                continue

            ack = {}
            type = msg['msg']
            ack['msg'] = type

            try:
                if type == 1: #连接请求
                    address = (msg['data']['addr'], msg['data']['port'])
                    try:
                        Sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        Sock.connect(address)
                        sockmap[maxchannel] = Sock
                        ack['ret'] = 0
                        ack['channel'] = maxchannel
                        maxchannel += 1
                    except BaseException,e:
                        ack['ret'] = 1
                        ack['data'] = u"连接失败"
                    self.sock.send(json.dumps(ack))
                    print "send:",json.dumps(ack)

                if type == 2: #断开请求
                    channel = msg['channel']
                    if channel in sockmap:
                        sockmap[channel].close()
                        sockmap[channel] = None
                    ack['ret'] = 0
                    self.sock.send(json.dumps(ack))
                    print "send:", json.dumps(ack)

                if type == 3: #数据发送
                    channel = msg['channel']
                    if channel in sockmap:
                        try:
                            data = msg['data']
                            data = "".join([chr(x) for x in data])
                            sockmap[channel].send(data)
                            ack['ret'] = 0
                        except BaseException:
                            ack['ret'] = 1
                            ack['data'] = u"发送失败"
                    else:
                        ack['ret'] = 1
                        ack['data'] = u"连接不存在"
                    self.sock.send(json.dumps(ack))
                    print "send:", json.dumps(ack)

                if type == 4: #数据接收
                    channel = msg['channel']
                    if channel in sockmap:
                        ack['ret'] = 0

                        try:
                            data = sockmap[channel].recv(4096)
                            if data == None or len(data) < 1:
                                ack['ret'] = 1
                            data = [ord(x) for x in data]
                            ack['data'] = data
                        except BaseException,e:
                            if "timed out" not in e:
                                ack['ret'] = 1
                    else:
                        ack['ret'] = 2
                        ack['data'] = u"连接不存在"

                    self.sock.send(json.dumps(ack))
                    print "send:", json.dumps(ack)

            except BaseException,e:
                self.status = 1
                return

def clientauth(tcpSerSock):

    try:
        tcpSerSock.connect(serveraddr)
        data = {'client': 1}
        tcpSerSock.send(json.dumps(data))

        starttime = time.time()
        while True:
            if time.time() - starttime > 2000:
                return 1

            try:
                data = tcpSerSock.recv(4096)
            except BaseException,e:
                if "timed out" in e:
                    continue
                return 1

            if data == None or len(data) < 1:
                return 1

            msg = json.loads(data)
            if 'result' not in msg or 'msg' not in msg:
                return 1

            if msg['result'] != 0:
                print msg['msg']
                return 1

            break

    except BaseException:
        return 1

    return 0

if __name__ == '__main__':
    tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    clientauth(tcpSerSock)
    ClientTransfer(tcpSerSock).start()
    input(u"输入任意键结束")


