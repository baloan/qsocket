#!python3
# encoding: utf8

import pickle
from queue import Queue
import select
import socket
import struct
from threading import Thread, Lock, Event


def create_qsocket(addr):
    socket = socket.create_connection(addr)
    qs = QSocket(socket)
    qs.start()
    return qs


class QSocket():
    """ Threadsafe socket connection """
    # https://docs.python.org/3/howto/sockets.html#socket-howto

    def __init__(self, sock):
        self.inq = Queue()
        self.sock = sock
        self.threads = {}
        self.sock_lock = Lock()
        self.pump = Thread(target=self.receive, daemon=True)
        self.terminate = False

    def start(self):
        self.pump.start()

    def send(self, obj):
        obj_bytes = pickle.dumps(obj)
        # max size of "i" is 4 bytes i.e. 2GB
        obj_len = struct.pack("i", len(obj_bytes))
        # lock socket only while sending
        with self.sock_lock:
            print("Sending {} bytes...".format(len(obj_bytes)))
            self.sock.sendall(obj_len + obj_bytes)

    def close(self):
        self.terminate = True

    def receive(self):
        size_header = struct.calcsize("i")
        try:
            while not self.terminate:
                # timeout wait for data to become available
                sread, _, _ = select.select([self.sock], [], [], 1)
                if sread != []:
                    # lock socket only while receiving
                    with self.sock_lock:
                        print("Receiving...")
                        b = self.recv_bytes(size_header)
                        if b is None:
                            break
                        obj_len = struct.unpack("i", b)[0]
                        print("Receiving {} bytes".format(obj_len))
                        obj_bytes = self.recv_bytes(obj_len)
                    obj = pickle.loads(obj_bytes)
                    self.process(obj)
        finally:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

    def recv_bytes(self, n):
        chunks = []
        received = 0
        while received < n:
            chunk = self.sock.recv(n - received)
            chunks.append(chunk)
            received = received + len(chunk)
        return b''.join(chunks)

    def process(self, obj):
        self.inq.put(obj)


class Listener(Thread):

    def __init__(self, addr=("", 8080), socket_class=QSocket):
        Thread.__init__(self)
        self.addr = addr
        self.socket_class = socket_class
        self.sockq = Queue()
        self.terminate = False

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print("Binding to {}".format(self.addr))
            s.bind(self.addr)
            s.listen(2)
            while not self.terminate:
                # timeout wait for connection to become available
                sread, _, _ = select.select([s], [], [], 1)
                if sread != []:
                    sock, _ = s.accept()
                    qs = self.socket_class(sock)
                    qs.start()
                    self.sockq.put(qs)

    def close(self):
        self.terminate = True
