#!/usr/bin/env python3

import argparse
import sys
from pycoin.tx import Tx

from models import txs, known_txs, unprocessed_txs, addr_to_uid, Account, known_blocks, all_addresses
from wallet import process_tx_initial

parser = argparse.ArgumentParser()
parser.add_argument('--tx-hex')
parser.add_argument('--txid')
args = parser.parse_args()

if args.txid in known_txs:
    sys.exit()

tx = Tx.tx_from_hex(args.tx_hex)
process_tx_initial(tx)

