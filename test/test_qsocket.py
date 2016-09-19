#!/usr/bin/python3.5
# encoding: utf8

"""qsocket test suite"""

import threading
import multiprocessing as mp
from time import sleep
import unittest
import time

from qsocket import QSocket, Listener, create_qsocket


class Echo(QSocket):

    def __init__(self, socket):
        QSocket.__init__(self, socket)

    def process(self, obj):
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
        self.bob = self.listener.accept()
        print("[{}] [{}] runs {} ----------".format(
            threading.current_thread().name, threading.current_thread().ident, self.id()))
        print("self.listener {}".format(self.listener))
        print("self.alice    {}".format(self.alice.receiver_t))
        print("self.bob      {}".format(self.bob.receiver_t))

    def test_string(self):
        req = "Hello echo!"
        self.alice.send(req)
        resp = self.alice.recv()
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
        self.bob = self.listener.accept()
        print("[{}] [{}] runs {} ----------".format(
            threading.current_thread().name, threading.current_thread().ident, self.id()))
        print("self.listener {}".format(self.listener))
        print("self.alice    {}".format(self.alice.receiver_t))
        print("self.bob      {}".format(self.bob.receiver_t))

    def tearDown(self):
        print("[{}] [{}] closing all sockets".format(
            threading.current_thread().name, threading.current_thread().ident))
        self.alice.close()
        self.bob.close()
        self.listener.close()

    def test_ping_pong(self):
        # alice sends an update
        req = {"action": "subscribe", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.recv()
        self.assertEqual(req, resp)
        # bob sends an update
        req = {"action": "update", "name": "foo", "value": 120.2}
        self.bob.send(req)
        resp = self.alice.recv()
        self.assertEqual(req, resp)

    def test_remote_close(self):
        # alice sends an update
        req = {"action": "create", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.recv()
        self.assertEqual(req, resp)
        self.bob.close(wait=True)
        # wait for remote socket close (needs select timeout)
        sleep(QSocket.SELECT_TIMEOUT)
        req = {"action": "update", "name": "foo", "value": 120.2}
        self.assertRaises(OSError, self.alice.send, req)

    def test_remote_close2(self):
        # alice sends an update
        req = {"action": "create", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.recv()
        self.assertEqual(req, resp)
        self.bob.close(wait=True)
        # local inq None: socket closed
        resp = self.bob.recv()
        self.assertEqual(resp, None)
        # inq None: socket closed
        resp = self.alice.recv()
        self.assertEqual(resp, None)

    def test_local_close(self):
        # alice sends an update
        req = {"action": "create", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.recv()
        self.assertEqual(req, resp)
        self.alice.close(wait=True)
        # wait for remote socket close (needs select timeout)
        sleep(QSocket.SELECT_TIMEOUT)
        req = {"action": "update", "name": "foo", "value": 120.2}
        self.assertRaises(OSError, self.bob.send, req)

    def test_local_close2(self):
        # alice sends an update
        req = {"action": "create", "name": "foo", }
        self.alice.send(req)
        resp = self.bob.recv()
        self.assertEqual(req, resp)
        self.alice.close(wait=True)
        # local inq None: socket closed
        resp = self.alice.recv()
        self.assertEqual(resp, None)
        # remote inq None: socket closed
        resp = self.bob.recv()
        self.assertEqual(resp, None)


def bob(laddr, socket_class):
    print("{}:{} [{}] runs ----------".format(mp.current_process().pid,
                                              threading.current_thread().ident,
                                              threading.current_thread().name))
    listener = Listener(laddr, socket_class)
    listener.start()
    qsocket = listener.accept()
    print("{} connection accepted".format(mp.current_process()))
    print("self.listener {}".format(listener))
    print("self.qsocket  {}".format(qsocket.receiver_t))
    # wait for close
    _ = qsocket.recv()
    print("{} closing socket".format(mp.current_process()))
    listener.close()


class NonFunctional(unittest.TestCase):

    def setUp(self):
        port = 8022
        laddr = ("", port)
        raddr = ("127.0.0.1", port)
        # Server
        proc = mp.Process(target=bob, args=(laddr, Echo,))
        proc.start()
        # Client
        self.alice = create_qsocket(raddr)
        print("self.alice connected from {} to {}".format(
            self.alice.sock.getsockname(), self.alice.sock.getpeername()))
        print("[{}] [{}] runs {} ----------".format(
            threading.current_thread().name, threading.current_thread().ident, self.id()))
        print("self.alice    {}".format(self.alice.receiver_t))

    def tearDown(self):
        print("[{}] [{}] closing all sockets".format(
            threading.current_thread().name, threading.current_thread().ident))
        self.alice.close()

    def test_size_ladder(self):
        sleep(1)
        sizes = (100, 1000, 10000, 100000, 1000000, 10000000,)
        for s in sizes:
            send_buffer = b'i' * s
            t0 = time.perf_counter()
            self.alice.send(send_buffer)
            recv_buffer = self.alice.recv()
            self.assertEqual(send_buffer, recv_buffer)
            t1 = time.perf_counter()
            td = t1 - t0
            print(
                "echo ping-pong of {:10} bytes took {:4.4f}s, {:9.0f}kB/s".format(len(send_buffer), td, s / 1000 / td))
