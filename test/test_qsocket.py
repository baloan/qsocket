#!/usr/bin/python3.5
# encoding: utf8

"""qsocket"""

from pprint import pprint
import unittest
import socket
from qsocket import QSocket, Listener


class Echo(QSocket):
    def __init__(self, socket):
        QSocket.__init__(self, socket)

    def process(self, obj):
        self.send(obj)


class PassiveEchoServer(unittest.TestCase):
    def setUp(self):
        addr = ("", 8010)
        self.listener = Listener(addr, Echo)
        self.listener.start()

    def tearDown(self):
        print("Close listener socket {}".format(self.listener))
        self.listener.close()

    def test_echo(self):
        addr = ("127.0.0.1", 8010)
        sock = socket.create_connection(addr)
        print("Connected to {}".format(sock))
        qs = QSocket(sock)
        qs.start()
        qs.send("Hello world!")
        buf = qs.inq.get()
        print(buf)
        echo_sock = self.listener.sockq.get()
        print("Close echo socket {}".format(echo_sock))
        echo_sock.close()
        print("Close active socket {}".format(qs))
        qs.close()
