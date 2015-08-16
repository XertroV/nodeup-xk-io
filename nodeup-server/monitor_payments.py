#!/usr/bin/env python3

import time

from bitcoinrpc import connect_to_local
from pycoin.tx import Tx
from blockchain.blockexplorer import get_tx

from models import last_block_checked, unprocessed_txs, Account, addr_to_uid, nodes_recently_updated, txs, all_addresses
from constants import REQUIRED_CONFIRMATIONS, COIN
from digitalocean import calc_node_minutes

bitcoind = connect_to_local()

while True:
    best_block_hash = bitcoind.getbestblockhash()
    top_height = bitcoind.getblock(best_block_hash)['height']
    if best_block_hash == last_block_checked.get():
        time.sleep(10)  # only do this at most once per block
        continue
    last_block_checked.set(best_block_hash)

    for txid in unprocessed_txs.members():
        tx = Tx.tx_from_hex(txs[txid])
        tx_blockchain = get_tx(txid)
        if tx_blockchain.block_height == -1:
            continue
        if top_height - tx_blockchain.block_height >= REQUIRED_CONFIRMATIONS:
            unprocessed_txs.remove(txid)
            for out in tx.txs_out:
                address = out.address()
                if address not in all_addresses:
                    continue
                account = Account(addr_to_uid[address])
                satoshis = out.coin_value
                account.total_coins.incr(satoshis)
                node_minutes_d = calc_node_minutes(satoshis)
                account.total_minutes.incr(node_minutes_d)
                account.add_msg('Detected payment via txid: %s' % (tx['txid'],))
                account.add_msg('Increased total paid by %.8f to %.8f' % (out.coin_value / COIN, account.total_coins.get() / COIN))
                account.add_msg('Increased node life by %d minutes; expiring around %d' % (node_minutes_d, account.get_expiry().isoformat()))
                nodes_recently_updated.append(account.uid)