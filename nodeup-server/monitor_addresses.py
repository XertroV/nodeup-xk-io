#!/usr/bin/env python3

import time

from bitcoinrpc import connect_to_local

from models import unused_addresses
from constants import REQUIRED_CONFIRMATIONS, COIN
from digitalocean import calc_node_minutes

bitcoind = connect_to_local()

DESIRED_N_ADDRESSES = 500

while True:
    if len(unused_addresses) < 500:
        for i in range(DESIRED_N_ADDRESSES - len(unused_addresses)):
            unused_addresses.append(bitcoind.getnewaddress())
    else:
        time.sleep(5)