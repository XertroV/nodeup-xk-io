import json
import hashlib
from decimal import Decimal
import datetime
import time

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
        if self.key not in db:
            return self.default
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
all_msgs = List(db, 'all_msgs')


# droplet management
vultr_api_key = SimpleKVPair(db, 'do_api_key', str)
droplets_to_configure = ZSet(db, 'droplets_to_configure')
droplet_to_uid = Hash(db, 'droplet_to_uid')
droplet_ips = Hash(db, 'droplet_ips')
currently_compiling = Set(db, 'currently_compiling')
nodes_currently_syncing = Set(db, 'currently_syncing')
active_servers = Set(db, 'active_servers')

class Account:
    def __init__(self, uid):
        self.db = db
        self.uid = uid
        # these need to be first for create_new_address()
        self.total_coins = SimpleKVPair(self.db, 'uid_total_coins:%s' % uid, int, default=0)
        self.total_minutes = SimpleKVPair(self.db, 'uid_total_minutes:%s' % uid, int, default=0)
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
        self.droplet_id = SimpleKVPair(db, 'droplet_id:%s' % uid, str)
        self.unconf_minutes = SimpleKVPair(db, 'unconf_mins:%s' % uid, int, default=0)
        self.compile_ts = SimpleKVPair(db, 'compile_ts:%s' % uid, int, default=0)
        self.destroyed = SimpleKVPair(db, 'destroyed:%s' % uid, bool, default=False)

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
        now = int(time.time())
        self.msgs.prepend("%d: %s" % (now, msg))
        all_msgs.prepend("%d, %s: %s" % (now, self.uid, msg))

    def get_expiry(self):
        if not self.node_created.get():
            return datetime.datetime.now() + datetime.timedelta(minutes=self.total_minutes.get())
        else:
            return datetime.datetime.fromtimestamp(self.creation_ts.get() + self.total_minutes.get() * 60)

    def destroy(self):
        self.destroyed.set(True)
        self.add_msg('Node destroyed. Please use a new account.')
        uid_to_addr[self.uid] = self.address + '-decommissioned'

    def pretty_string(self):
        return """Account: {uid}
    Address       : {address}
    # txs         : {n_txs}
    Total Coins   : {total_coins}
    Total Months  : {total_minutes}
    Server ID     : {server_id}
    Server IP     : {server_ip}
    Expiry        : {expiry}

    take 3 account.msgs
        {msgs}

""".format(uid=self.uid, address=self.address, n_txs=len(self.txs), total_coins=self.total_coins.get(),
           total_minutes=self.total_minutes.get(), server_id=self.droplet_id.get(), msgs=self.get_msgs(3),
           expiry=self.get_expiry().isoformat(), server_ip=droplet_ips[self.droplet_id.get()])