#!/usr/bin/env python3

import asyncio
import logging
import time
import hashlib
import signal
from binascii import hexlify

from pycoin.tx import Tx


from bitcoinlib.coredefs import *
from bitcoinlib.core import *
from bitcoinlib.messages import *
from bitcoinlib.logger import PrettyLog

from wallet import process_tx_initial

MY_VERSION = 313
MY_SUBVERSION = b"/bitcoinlib:0.0.1/"

# Default Settings if no configuration file is given
settings = {
        "host": "127.0.0.1",
        "port": 8333,
        "chain": "mainnet",
        "log": None,
        "debug": True
}
debugnet = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def new_block_event(block):
    if block.is_valid():
        logging.info("Valid Block: %s" % block.hash)

    else:
        logging.debug("Invalid Block: %s" % block.hash)

def new_transaction_event(tx):
    if tx.is_valid():
        logging.info("\n  Valid TX: %s\n" % (tx.hash.decode(),))
        process_tx_initial(Tx.tx_from_hex(hexlify(tx.serialize())))

def verbose_sendmsg(message):
    if debugnet:
        return True
    if message.command != b'getdata':
        return True
    return False

def verbose_recvmsg(message):
    skipmsg = {
       b'tx',
       b'block',
       b'inv',
       b'addr',
    }
    if debugnet:
        return True
    if message.command in skipmsg:
        return False
    return True


class BitcoinClient(asyncio.Protocol):

    def __init__(self, dstaddr, dstport, log, netmagic):
        self.dstaddr = dstaddr
        self.dstport = dstport
        self.log = log
        self.recvbuf = b""
        self.netmagic = netmagic

        self.ver_send = MIN_PROTO_VERSION
        self.ver_recv = MIN_PROTO_VERSION
        self.last_sent = 0
        self.getblocks_ok = True
        self.last_block_rx = time.time()
        self.last_getblocks = 0
        self.remote_height = -1
        self.nStartingHeight = -1

        # Don't think we need this
        # self.hash_continue = None

    def connection_made(self, transport):
        print("connection made!")
        self.transport = transport

        # Create msg version to initialize w/ dst node
        vt = msg_version()
        vt.addrTo.ip = self.dstaddr
        vt.addrTo.port = self.dstport
        vt.addrFrom.ip = "0.0.0.0"
        vt.addrFrom.port = 0
        vt.nStartingHeight = -1
        vt.strSubVer = MY_SUBVERSION
        self.send_message(vt)

    def data_received(self, data):
        try:
            self.recvbuf += data
            if len(self.recvbuf) <= 0: raise ValueError
        except (IOError, ValueError) as exc:
            errno, errstr = exc.args
            self.log("Data received error: " + errstr)
            self.connection_lost(exc)
            return
        self.got_data()

    def connection_lost(self, exc):
        print('server closed the connection')
        asyncio.get_event_loop().stop()

    def got_data(self):
        while True:
            if len(self.recvbuf) < 4:
                return
            if self.recvbuf[:4] != self.netmagic.msg_start:
                raise ValueError("got garbage: recbuf: %s netmagic: %s" % (repr(self.recvbuf[:4]), str(self.netmagic.msg_start)))
            # check checksum
            if len(self.recvbuf) < 4 + 12 + 4 + 4:
                return
            command = self.recvbuf[4:4+12].split(b'\x00', 1)[0]
            msglen = struct.unpack(b"<i", self.recvbuf[4+12:4+12+4])[0]
            checksum = self.recvbuf[4+12+4:4+12+4+4]
            if len(self.recvbuf) < 4 + 12 + 4 + 4 + msglen:
                return
            msg = self.recvbuf[4+12+4+4:4+12+4+4+msglen]
            th = hashlib.sha256(msg).digest()
            h = hashlib.sha256(th).digest()
            if checksum != h[:4]:
                raise ValueError("got bad checksum %s" % repr(self.recvbuf))
            self.recvbuf = self.recvbuf[4+12+4+4+msglen:]

            if command in messagemap:
                f = io.BytesIO(msg)
                t = messagemap[command](self.ver_recv)
                t.deserialize(f)
                self.got_message(t)
            else:
                self.log.debug("UNKNOWN COMMAND %s %s" % (command, repr(msg)))

    def send_message(self, message):
        if verbose_sendmsg(message):
            self.log.info("send %s" % repr(message))

        tmsg = message_to_str(self.netmagic, message)

        try:
            self.transport.write(tmsg)
            self.last_sent = time.time()
        except:
            _, exc, _ = sys.exc_info()
            self.connection_lost(exc)

    def got_message(self, message):

        if self.last_sent + 30 * 60 < time.time():
            self.send_message(msg_ping(self.ver_send))

        if verbose_recvmsg(message):
            self.log.info("recv %s" % repr(message))

        if message.command == b"version":
            self.ver_send = min(PROTO_VERSION, message.nVersion)
            if self.ver_send < MIN_PROTO_VERSION:
                self.log.debug("Obsolete version %d, closing" % (self.ver_send,))
                self.connection_lost()
                return

            if (self.ver_send >= NOBLKS_VERSION_START and
                self.ver_send <= NOBLKS_VERSION_END):

                self.send_message(msg_verack(self.ver_send))
            if self.ver_send >= CADDR_TIME_VERSION:
                self.send_message(msg_getaddr(self.ver_send))

        elif message.command == b"verack":
            self.ver_recv = self.ver_send

        elif message.command == b"ping":
            if self.ver_send > BIP0031_VERSION:
                self.send_message(msg_pong(self.ver_send))

        elif message.command == b"inv":

            want = msg_getdata(self.ver_send)
            for i in message.inv:
                if i.type == 1:
                    want.inv.append(i)
                elif i.type == 2:
                    want.inv.append(i)
            if len(want.inv):
                self.send_message(want)

        elif message.command == b"tx":
            new_transaction_event(message.tx)

        elif message.command == b"block":
            new_block_event(message.block)


def initialize_client():
    chain = settings['chain']
    if chain not in NETWORKS:
        log.warning("invalid network")
        sys.exit(1)
    netmagic = NETWORKS[chain]
    return BitcoinClient(settings['host'], settings['port'], logging, netmagic)


def run():
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    c = initialize_client()
    coro = loop.create_connection(lambda: c, '127.0.0.1', 8333)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()

if __name__ == '__main__':
    run()
