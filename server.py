#-*- coding:utf-8 -*-
import socket
import threading
import json
import time
import signal
import sys

portmap = {5907:[1, {'addr':"127.0.0.1", 'port':5900}]} #每个客户的公网端口到内网端口的映射，外网端口->客户号、内网地址、端口
sockmap = {} #客户号和内网主机连接的对应关系 客户号->socket
listenport = 6000
socket.setdefaulttimeout(1)

class ClientListener(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        host = ''
        addr = (host, listenport)
        tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSerSock.bind(addr)
        tcpSerSock.listen(20)

        try:
            while True:
                try:
                    sock,client_addr = tcpSerSock.accept()
                    print "connect client:",client_addr
                    ClientAuth(sock).start()
                except KeyboardInterrupt:
                    sys.exit()
                except BaseException,e:
                    if "timed out" in e:
                        continue

                    return
        except KeyboardInterrupt:
            sys.exit()

class ClientAuth(threading.Thread): #客户端认证
    def __init__(self, sock):
        threading.Thread.__init__(self)
        self.sock = sock
        self.starttime = time.time()

    def run(self):
        result = 1
        retmsg = ""
        client = 0
        data = ""

        try:
            while True:
                try:
                    data = self.sock.recv(4096)

                    if data == None or len(data) < 1:
                        self.sock.close()
                        return

                    print "recv:",data
                except KeyboardInterrupt:
                    sys.exit()
                except BaseException,e:
                    if 'timed out' not in e:
                        self.sock.close()
                        return

                    if time.time() - self.starttime > 60:
                        print "auth timeout"
                        self.sock.close()
                        return

                try:
                    data = json.loads(data)
                except KeyboardInterrupt:
                    sys.exit()
                except BaseException:
                    self.sock.close()
                    retmsg = "invalid auth"
                    print retmsg

                if "client" not in data:
                    self.sock.close()
                    retmsg = "must contain auth info"
                else:
                    result = 0
                    client = data["client"]

                    retmsg = "auth success,client:"+str(client)+",addr:"
                    print retmsg
                    print self.sock

                data = {'result':result, 'msg':retmsg}
                try:
                    self.sock.send(json.dumps(data))
                    print "send:",json.dumps(data)
                except KeyboardInterrupt:
                    sys.exit()
                except BaseException:
                    self.sock.close()
                    return

                sockmap[int(client)] = self.sock

                return
        except KeyboardInterrupt:
            sys.exit()

class PortListener(threading.Thread):
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.port = port

    def run(self):
        global portmap, sockmap

        try:
            while True:
                if self.port not in portmap:
                    continue

                if portmap[self.port] == None:
                    continue

                client = portmap[self.port][0]
                if client not in sockmap or sockmap[client] == None:
                    continue

                break

            addr = ('', self.port)
            tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcpSerSock.bind(addr)
            tcpSerSock.listen(20)

            while True:
                try:
                    sock, clientaddr = tcpSerSock.accept()
                    print "client connect:",clientaddr
                except KeyboardInterrupt:
                    sys.exit()
                except BaseException,e:
                    continue
                if self.port not in portmap:
                    sock.close()
                PortTransfer(self.port, sock).start()
        except KeyboardInterrupt:
            sys.exit()

def waitremoteack(remotesock, msg=None, ret=None):
    starttime = time.time()

    try:
        while True:
            if time.time() - starttime > 20:
                return -1

            try:
                data = remotesock.recv(4096)

                if data == None or len(data) < 1:
                    return -2

                print "recv:", data
            except KeyboardInterrupt:
                sys.exit()
            except BaseException,e:
                if "timed out" in e:
                    continue

                return -2

            try:
                ack = json.loads(data)
            except KeyboardInterrupt:
                sys.exit()
            except BaseException:
                return -1

            if msg == None:
                return ack

            if 'msg' not in ack or "ret" not in ack:
                return -1

            if ack['msg'] != 1:
                return -1

            if ack['ret'] != 0:
                return -1

            if 'channel' not in ack or ack['channel'] == None:
                return -1

            return ack['channel']
    except KeyboardInterrupt:
        sys.exit()

class PortTransfer(threading.Thread):
    def __init__(self, port, sock):
        threading.Thread.__init__(self)
        self.port = port
        self.sock = sock
        self.channel = None

    def send(self,remotesock, data):
        if len(data) > 0:
            data = [ord(x) for x in data]
            msg = {'msg': 3, 'channel': self.channel, 'data': data}
            try:
                remotesock.send(json.dumps(msg))
                print "send:",json.dumps(msg)
            except KeyboardInterrupt:
                sys.exit()
            except BaseException,e:
                print e
                self.sock.close()
                return -1

            ack = waitremoteack(remotesock)
            if ack == -1:
                return 0

            try:
                ack = json.loads(ack)
                if ack['ret'] == 1:
                    self.sock.close()
            except KeyboardInterrupt:
                sys.exit()
            except BaseException:
                return 0

    def recv(self, remotesock):
        msg = {'msg': 4, 'channel': self.channel}
        try:
            remotesock.send(json.dumps(msg))
            print "send:", json.dumps(msg)
        except KeyboardInterrupt:
            sys.exit()
        except BaseException,e:
            print e
            self.sock.close()
            return -1

        ack = waitremoteack(remotesock)
        if ack == -2:
            self.sock.close()
            return -1

        if 'ret' in ack and ack['ret'] == 1:
            self.sock.close()
            return -1

        if 'data' in ack and ack['ret'] == 0:
            data = ack['data']
            if len(data) < 1:
                return 0

            try:
                data = "".join([chr(x) for x in data])
                self.sock.send(data)
                print "send:", data
            except KeyboardInterrupt:
                sys.exit()
            except BaseException,e:
                print e
                return -1

        return 0

    def run(self):
        global portmap, sockmap

        if self.port not in portmap:
            self.sock.close()
            return

        if portmap[self.port] == None:
            self.sock.close()
            return

        client = portmap[self.port][0]
        if client not in sockmap or sockmap[client] == None:
            self.sock.close()
            return

        remotesock = sockmap[client] #远程要穿透的内网连接

        #向客户端发送连接请求消息
        msg = {'msg':1}
        msg['data'] = portmap[self.port][1]
        data = json.dumps(msg)
        try:
            remotesock.send(data)
            print "send:", data
        except KeyboardInterrupt:
            sys.exit()
        except BaseException:
            self.sock.close()
            return

        #等待响应
        self.channel = waitremoteack(remotesock, 1, 0)
        if self.channel == -1:
            self.sock.close()
            return

        try:
            while True:
                if self.port not in portmap:
                    self.sock.close()
                    # 发送断开消息
                    msg = {'msg': 2, 'channel': self.channel}
                    data = json.dumps(msg)
                    try:
                        remotesock.send(data)
                        print "send:", data
                    except KeyboardInterrupt:
                        sys.exit()
                    except BaseException:
                        return
                    waitremoteack(remotesock, 2, 0)
                    return

                connbreak = 0
                data = ""
                try:
                    data = self.sock.recv(4096)

                    if data == None or len(data) < 1:
                        connbreak = 1

                    print "recv:", data
                except KeyboardInterrupt:
                    sys.exit()
                except BaseException,e:
                    if "timed out" not in e:
                        connbreak = 1

                if connbreak == 1:
                    #发送断开消息
                    msg = {'msg': 2, 'channel':self.channel}
                    data = json.dumps(msg)
                    try:
                        remotesock.send(data)
                        print "send:", data
                    except KeyboardInterrupt:
                        sys.exit()
                    except BaseException:
                        return
                    waitremoteack(remotesock, 2, 0)
                    return

                #正常发送数据
                if self.send(remotesock, data) == -1:
                    return

                if self.recv(remotesock) == -1:
                    return
        except KeyboardInterrupt:
            sys.exit()

def exit(signum, frame):
    print('You choose to stop me.')
    sys.exit()

if __name__ == '__main__':
    ClientListener().start()

    for p in portmap:
        PortListener(p).start()

    # input("press any key:")
    # signal.signal(signal.SIGINT, exit)
    # signal.signal(signal.SIGTERM, exit)
    # while True:
    #     time.sleep(10)
    #     continue

    try:
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit()

