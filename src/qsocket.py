#!python3
# encoding: utf8

import pickle
from queue import Queue
import select
import socket
import struct
from threading import Thread, Lock, Event
from pprint import pprint
import sys

SELECT_TIMEOUT = 1.0


def create_qsocket(addr):
    socket = socket.create_connection(addr)
    return QSocket(socket)


class QSocket():
    """ Threadsafe socket connection """
    PACK_FMT = "!i"
    PACK_SIZE = struct.calcsize(PACK_FMT)
    # https://docs.python.org/3/howto/sockets.html#socket-howto

    def __init__(self, sock):
        self.inq = Queue()
        self.sock = sock
        # self.sock.settimeout(1.0)
        self.threads = {}
        self.sock_lock = Lock()
        self.terminate = Event()
        self.pump = Thread(target=self.receive, daemon=True)
        self.pump.start()

    def send(self, obj):
        if obj is None:
            raise ValueError()
        obj_bytes = pickle.dumps(obj)
        # max size of "i" is 4 bytes i.e. 2GB
        obj_len = struct.pack(QSocket.PACK_FMT, len(obj_bytes))
        buffer = b''.join((obj_len, obj_bytes))
        # pprint(buffer)
        with self.sock_lock:
            self.sock.sendall(buffer)

    def close(self, wait=False):
        self.terminate.set()
        if wait:
            self.pump.join()

    def receive(self):
        try:
            while not self.terminate.is_set():
                # timeout wait for data to become available
                sread, _, _ = select.select([self.sock], [], [], SELECT_TIMEOUT)
                if sread != []:
                    len_bytes = self.recv_bytes(QSocket.PACK_SIZE)
                    obj_len = struct.unpack(QSocket.PACK_FMT, len_bytes)[0]
                    obj_bytes = self.recv_bytes(obj_len)
                    obj = pickle.loads(obj_bytes)
                    self.process(obj)
        except OSError as e:
            print(e, file=sys.stderr)
        finally:
            with self.sock_lock:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            self.process(None)

    def recv_bytes(self, n):
        chunks = []
        received = 0
        while received < n:
            # add a timeout to protect again partly frozen source
            # lock socket only while receiving
            with self.sock_lock:
                chunk = self.sock.recv(n - received)
            if len(chunk) == 0:
                raise BrokenPipeError("[{}] [{}] Remote socket closed, Local {}, Remote {}".format(
                    self.pump.name, self.pump.ident, self.sock.getsockname(), self.sock.getpeername()))
            chunks.append(chunk)
            received = received + len(chunk)
        return b''.join(chunks)

    def process(self, obj):
        self.inq.put(obj)


class Listener(Thread):

    def __init__(self, addr=("", 8080), socket_class=QSocket):
        Thread.__init__(self, name="Port-{}".format(addr[1]))
        self.addr = addr
        self.socket_class = socket_class
        self.sockq = Queue()
        self.terminate = Event()

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(self.addr)
            s.listen()
            while not self.terminate.is_set():
                # timeout wait for connection to become available
                sread, _, _ = select.select([s], [], [], SELECT_TIMEOUT)
                if sread != []:
                    sock, _ = s.accept()
                    qs = self.socket_class(sock)
                    self.sockq.put(qs)
        self.sockq.put(None)

    def close(self, wait=False):
        self.terminate.set()
        if wait:
            self.join()
