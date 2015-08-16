#!/usr/bin/env python3

import argparse
import json
import sys
import io
from binascii import unhexlify, hexlify

from bitcoinrpc import connect_to_local
from pycoin.block import Block

from models import txs, known_txs, unprocessed_txs, addr_to_uid, Account, known_blocks, all_addresses
from wallet import process_tx_initial

parser = argparse.ArgumentParser()
parser.add_argument('--blockhash')
args = parser.parse_args()

blockhash = args.blockhash
if blockhash in known_blocks:
    sys.exit()

bitcoind = connect_to_local()
block_hex = bitcoind.getblock(blockhash, False)
block = Block.parse(io.BytesIO(unhexlify(block_hex)))
for tx in block.txs:
    process_tx_initial(tx)

