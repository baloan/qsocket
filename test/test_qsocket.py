#!/usr/bin/python3.5
# encoding: utf8

"""qsocket"""

from pprint import pprint
import unittest
import socket
from qsocket import QSocket, Listener
from time import sleep
import threading


class Echo(QSocket):

    def __init__(self, socket):
        QSocket.__init__(self, socket)

    def process(self, obj):
        if obj is not None:
            self.send(obj)


class EchoServer(unittest.TestCase):

    def test_string(self):
        port = 8020
        laddr = ("", port)
        raddr = ("127.0.0.1", port)
        listener = Listener(laddr, Echo)
        listener.start()
        sock = socket.create_connection(raddr)
        alice = QSocket(sock)
        bob = listener.sockq.get()
        print("Running threads:")
        print("Main     {}".format(threading.current_thread()))
        print("Listener {}".format(listener))
        print("Alice    {}".format(alice.pump))
        print("Bob      {}".format(bob.pump))
        req = "Hello echo!"
        alice.send(req)
        resp = alice.inq.get()
        self.assertEqual(req, resp)
        listener.close()
        alice.close()
        bob.close()


class SocketClose(unittest.TestCase):

    def test_baseline(self):
        port = 8021
        laddr = ("", port)
        raddr = ("127.0.0.1", port)
        # Server
        listener = Listener(laddr)
        listener.start()
        # Client
        sock = socket.create_connection(raddr)
        alice = QSocket(sock)
        # Bob open connection
        bob = listener.sockq.get()
        print("Running threads:")
        print("Main     {}".format(threading.current_thread()))
        print("Listener {}".format(listener))
        print("Alice    {}".format(alice.pump))
        print("Bob      {}".format(bob.pump))
        # Alice sends an update
        req = {"action": "subscribe", "name": "foo", }
        alice.send(req)
        resp = bob.inq.get()
        self.assertEqual(req, resp)
        # Bob sends an update
        req = {"action": "update", "name": "foo", "value": 120.2}
        bob.send(req)
        resp = alice.inq.get()
        self.assertEqual(req, resp)
        # close all sockets
        bob.close()
        alice.close()
        listener.close()

    def test_remote_close(self):
        port = 8022
        laddr = ("", port)
        raddr = ("127.0.0.1", port)
        # Server
        listener = Listener(laddr)
        listener.start()
        # Client
        sock = socket.create_connection(raddr)
        alice = QSocket(sock)
        # Bob open connection
        bob = listener.sockq.get()
        print("Running threads:")
        print("Main     {}".format(threading.current_thread()))
        print("Listener {}".format(listener))
        print("Alice    {}".format(alice.pump))
        print("Bob      {}".format(bob.pump))
        # Alice sends an update
        req = {"action": "create", "name": "foo", }
        alice.send(req)
        resp = bob.inq.get()
        self.assertEqual(req, resp)
        bob.close(wait=True)
        # Alice sends an update
        req = {"action": "update", "name": "foo", "value": 120.2}
        self.assertRaises(OSError, alice.send, req)
        # close all sockets
        alice.close()
        listener.close()

    def test_local_close(self):
        port = 8023
        laddr = ("", port)
        raddr = ("127.0.0.1", port)
        # Server
        listener = Listener(laddr)
        listener.start()
        # Client
        sock = socket.create_connection(raddr)
        alice = QSocket(sock)
        # Bob open connection
        bob = listener.sockq.get()
        print("Running threads:")
        print("Main     {}".format(threading.current_thread()))
        print("Listener {}".format(listener))
        print("Alice    {}".format(alice.pump))
        print("Bob      {}".format(bob.pump))
        # Alice sends an update
        req = {"action": "create", "name": "foo", }
        alice.send(req)
        resp = bob.inq.get()
        self.assertEqual(req, resp)
        alice.close(wait=True)
        # Bob sends an update
        req = {"action": "update", "name": "foo", "value": 120.2}
        self.assertRaises(OSError, bob.send, req)
        # close all sockets
        bob.close()
        listener.close()
