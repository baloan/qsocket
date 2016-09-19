#!python3
# encoding: utf8

# Copyright (C) 2016 Andreas Balogh
# Published under the MIT LICENCE, See LICENCE for details.

"""
A Queue like socket interface with multithreading. The QSocket class
send and receives any Python object which can be pickled. pickle is
used as serialisation mechanism.
"""

import pickle
from queue import Queue
import select
import socket
import struct
import sys
from threading import Thread, Lock, Event

import multiprocessing as mp


def create_qsocket(addr):
    sock = socket.create_connection(addr)
    return QSocket(sock)


class QSocket():
    """ Threadsafe socket connection """
    # https://docs.python.org/3/howto/sockets.html#socket-howto
    PACK_FMT = "!i"
    PACK_SIZE = struct.calcsize(PACK_FMT)
    SELECT_TIMEOUT = 0.1

    def __init__(self, sock):
        self.inq = Queue()
        self.sock = sock
        self.sock.setblocking(True)
        self.threads = {}
        self.sock_access = Lock()
        self.terminate = Event()
        self.receiver_t = Thread(target=self._receiver, daemon=True)
        self.receiver_t.start()

    def recv(self):
        return self.inq.get()

    def send(self, obj):
        obj_bytes = pickle.dumps(obj)
        # max size of "i" is 4 bytes i.e. 2GB
        obj_len = struct.pack(QSocket.PACK_FMT, len(obj_bytes))
        buffer = b''.join((obj_len, obj_bytes))
        with self.sock_access:
            self.sock.sendall(buffer)

    def _receiver(self):
        try:
            while not self.terminate.is_set():
                # timeout wait for data to become available
                sread, _, _ = select.select([self.sock], [], [], QSocket.SELECT_TIMEOUT)
                if sread != []:
                    len_bytes = self.recv_bytes(QSocket.PACK_SIZE)
                    obj_len = struct.unpack(QSocket.PACK_FMT, len_bytes)[0]
                    obj_bytes = self.recv_bytes(obj_len)
                    obj = pickle.loads(obj_bytes)
                    self.process(obj)
        except OSError as e:
            print(e, file=sys.stderr)
        finally:
            # call on_close while socket is still open
            self.on_close()
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

    def recv_bytes(self, n):
        chunks = []
        received = 0
        while received < n:
            with self.sock_access:
                chunk = self.sock.recv(n - received)
            if len(chunk) == 0:
                raise BrokenPipeError("{}:{} [{}] Remote socket closed, Local {}, Remote {}".format(
                    mp.current_process().pid, self.receiver_t.ident, self.receiver_t.name, self.sock.getsockname(), self.sock.getpeername()))
            chunks.append(chunk)
            received = received + len(chunk)
        return b''.join(chunks)

    def process(self, obj):
        self.inq.put(obj)

    def on_close(self):
        self.inq.put(None)

    def close(self, wait=False):
        self.terminate.set()
        if wait:
            self.receiver_t.join()


class Listener(Thread):
    ACCEPT_TIMEOUT = 1.0

    def __init__(self, addr=("", 8080), socket_class=QSocket):
        Thread.__init__(self, name="Port-{}".format(addr[1]))
        self.addr = addr
        self.socket_class = socket_class
        self.sockq = Queue()
        self.terminate = Event()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        self.sock.settimeout(Listener.ACCEPT_TIMEOUT)
        self.sock.bind(self.addr)
        self.sock.listen()
        while not self.terminate.is_set():
            try:
                cx, _ = self.sock.accept()
            except OSError as e:
                if str(e) == "timed out":
                    continue
                elif self.terminate.is_set():
                    break
                else:
                    print("{}:{} [{}] socket.accept() exception, {}".format(
                        mp.current_process().pid, self.ident, self.name, e), file=sys.stderr)
                    break
            self._connected(cx)
        self.sock.close()
        self.sockq.put(None)

    def _connected(self, cx):
        qs = self.socket_class(cx)
        self.sockq.put(qs)

    def accept(self):
        return self.sockq.get()

    def close(self, wait=False):
        self.terminate.set()
        self.sock.close()
        if wait:
            self.join()
