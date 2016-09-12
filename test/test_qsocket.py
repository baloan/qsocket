#!/usr/bin/python3.5
# encoding: utf8

"""qsocket"""

import threading
from time import sleep
import unittest

from qsocket import QSocket, Listener, create_qsocket, SELECT_TIMEOUT


class Echo(QSocket):

    def __init__(self, socket):
        QSocket.__init__(self, socket)

    def process(self, obj):
        # if obj is not None:
        self.send(obj)


class EchoServer(unittest.TestCase):

    def setUp(self):
        port = 8020
        laddr = ("", port)
        raddr = ("127.0.0.1", port)
        # Server
        self.listener = Listener(laddr, Echo)
        self.listener.start()
        # Client
        self.alice = create_qsocket(raddr)
        # self.bob open connection
        self.bob = self.listener.sockq.get()
        print("[{}] [{}] runs {} ----------".format(
            threading.current_thread().name, threading.current_thread().ident, self.id()))
        print("self.listener {}".format(self.listener))
        print("self.alice    {}".format(self.alice.pump))
        print("self.bob      {}".format(self.bob.pump))

    def test_string(self):
        req = "Hello echo!"
        self.alice.send(req)
        resp = self.alice.inq.get()
        self.assertEqual(req, resp)

    def tearDown(self):
        print("[{}] [{}] tearing down".format(
            threading.current_thread().name, threading.current_thread().ident))
        self.alice.close()
        self.bob.close()
        self.listener.close()


class SocketClose(unittest.TestCase):

    def setUp(self):
        port = 8021
        laddr = ("", port)
        raddr = ("127.0.0.1", port)
        # Server
        self.listener = Listener(laddr)
        self.listener.start()
        # Client
        self.alice = create_qsocket(raddr)
        # self.bob open connection
        self.bob = self.listener.sockq.get()
        print("[{}] [{}] runs {} ----------".format(
            threading.current_thread().name, threading.current_thread().ident, self.id()))
        print("self.listener {}".format(self.listener))
        print("self.alice    {}".format(self.alice.pump))
        print("self.bob      {}".format(self.bob.pump))

    def tearDown(self):
        print("[{}] [{}] closing all sockets".format(
            threading.current_thread().name, threading.current_thread().ident))
        self.alice.close()
        self.bob.close()
        self.listener.close()

    def test_ping_pong(self):
        # self.alice sends an update
        req = {"action": "subscribe", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.inq.get()
        self.assertEqual(req, resp)
        # self.bob sends an update
        req = {"action": "update", "name": "foo", "value": 120.2}
        self.bob.send(req)
        resp = self.alice.inq.get()
        self.assertEqual(req, resp)

    def test_remote_close(self):
        # self.alice sends an update
        req = {"action": "create", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.inq.get()
        self.assertEqual(req, resp)
        self.bob.close(wait=True)
        # wait for remote socket close (needs select timeout)
        sleep(SELECT_TIMEOUT)
        req = {"action": "update", "name": "foo", "value": 120.2}
        self.assertRaises(OSError, self.alice.send, req)

    def test_remote_close2(self):
        # self.alice sends an update
        req = {"action": "create", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.inq.get()
        self.assertEqual(req, resp)
        self.bob.close(wait=True)
        # local inq None: socket closed
        resp = self.bob.inq.get()
        self.assertEqual(resp, None)
        # inq None: socket closed
        resp = self.alice.inq.get()
        self.assertEqual(resp, None)

    def test_local_close(self):
        # self.alice sends an update
        req = {"action": "create", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.inq.get()
        self.assertEqual(req, resp)
        self.alice.close(wait=True)
        # wait for remote socket close (needs select timeout)
        sleep(SELECT_TIMEOUT)
        req = {"action": "update", "name": "foo", "value": 120.2}
        self.assertRaises(OSError, self.bob.send, req)

    def test_local_close2(self):
        # self.alice sends an update
        req = {"action": "create", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.inq.get()
        self.assertEqual(req, resp)
        self.alice.close(wait=True)
        # local inq None: socket closed
        resp = self.alice.inq.get()
        self.assertEqual(resp, None)
        # remote inq None: socket closed
        resp = self.bob.inq.get()
        self.assertEqual(resp, None)
