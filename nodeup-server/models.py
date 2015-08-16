import json
import hashlib
from decimal import Decimal
import datetime

from pycoin.key.BIP32Node import BIP32Node

from walrus.database import Hash, List, Set, ZSet, Database

from bitcoinrpc import connect_to_local

db = Database()

class SimpleKVPair:
    def __init__(self, db, key, type, default=None):
        self.key = key
        self.db = db
        self.type = type
        self.default = default

    def set(self, value):
        self.db[self.key] = value

    def get(self):
        if self.type is bool:
            if self.db[self.key] == b"False":
                return False
        try:
            r = self.type(self.db[self.key].decode())
        except KeyError:
            if self.default is None:
                r = self.type()
            else:
                if callable(self.default):
                    r = self.default()
                else:
                    r = self.type(self.default)
            self.set(r)
        return r

    def incr(self, n=1):
        return self.db.incr(self.key, n)


exchange_rate = SimpleKVPair(db, 'site:exchange_rate', float, default=1.0)  # USD/BTC - divide to turn dollars into bitcoin
node_accounts = Set(db, 'nodes_set')
total_nodeminutes = SimpleKVPair(db, 'stats:nodeminutes', int, default=0)
unused_addresses = List(db, 'unused_addresses')
addr_to_uid = Hash(db, 'addr_to_uid')
uid_to_addr = Hash(db, 'uid_to_addr')
txs = Hash(db, 'txs')
first_names = Hash(db, 'first_names')
known_txs = Set(db, 'known_txs')
unprocessed_txs = Set(db, 'unprocessed_txs')
last_block_checked = SimpleKVPair(db, 'last_block_checked', str, default=0)
nodes_recently_updated = List(db, 'nodes_recently_updated')
ssh_management_key = SimpleKVPair(db, 'ssh_management_key', str)
ssh_auditor_key = SimpleKVPair(db, 'ssh_auditor_key', str)
known_blocks = Set(db, 'known_blocks')
all_addresses = Set(db, 'all_addresses')
n_addresses = SimpleKVPair(db, 'n_addresses', int)
xpub = SimpleKVPair(db, 'xpub', str)


# droplet management
digitalocean_api_key = SimpleKVPair(db, 'do_api_key', str)
droplets_to_configure = ZSet(db, 'droplets_to_configure')
droplets_active = Set(db, 'droplets_active')
droplet_to_uid = Hash(db, 'droplet_to_uid')


class Account:
    def __init__(self, uid):
        self.db = db
        self.uid = uid
        # these need to be first for create_new_address()
        self.total_coins = SimpleKVPair(self.db, 'uid_total_coins:%s' % uid, Decimal)
        self.total_minutes = SimpleKVPair(self.db, 'uid_total_minutes:%s' % uid, Decimal)
        if uid not in uid_to_addr:
            self.create_new_address()
        self.address = uid_to_addr[uid].decode()
        self.txs = Set(db, 'txs_for:%s' % uid)
        self.msgs = List(db, 'msgs:%s' % uid)
        self.client = SimpleKVPair(self.db, 'client:%s' % uid, str, default='Bitcoin XT')
        self.tip = SimpleKVPair(self.db, 'tip:%s' % uid, float, default=0.1)
        self.email = SimpleKVPair(self.db, 'email:%s' % uid, str, default='')
        self.email_notify = SimpleKVPair(self.db, 'email_notify:%s' % uid, bool, default=False)
        self.name = SimpleKVPair(self.db, 'name:%s' % uid, str, default='')
        self.node_created = SimpleKVPair(self.db, 'node_created:%s' % uid, bool, default=False)
        self.creation_ts = SimpleKVPair(self.db, 'creation_ts:%s' % uid, int)
        self.droplet_id = SimpleKVPair(db, 'droplet_id:%s' % uid, int)
        self.unconf_minutes = SimpleKVPair(db, 'unconf_mins:%s' % uid, int)

    def create_new_address(self):
        n = n_addresses.incr()
        bip32node = BIP32Node.from_hwif(xpub.get())
        subkey = bip32node.subkey(0).subkey(n)  # match electrum path
        new_address = subkey.address()
        addr_to_uid[new_address] = self.uid
        uid_to_addr[self.uid] = new_address
        all_addresses.add(new_address)
        self.total_coins.set(0)
        self.total_minutes.set(0)
        return True

    def get_msgs(self, n=10):
        return self.msgs[:n]

    def add_msg(self, msg):
        self.msgs.prepend(msg)

    def get_expiry(self):
        if not self.node_created.get():
            return datetime.datetime.now() + datetime.timedelta(minutes=self.total_minutes.get())
        else:
            return datetime.datetime.fromtimestamp(self.creation_ts.get() + self.total_minutes.get() * 60)

