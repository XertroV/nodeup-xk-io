#!/usr/bin/env python3

import time
import logging

from bitcoinrpc import connect_to_local
from pycoin.tx import Tx
from blockchain.blockexplorer import get_tx, get_latest_block

from models import last_block_checked, unprocessed_txs, Account, addr_to_uid, nodes_recently_updated, txs, all_addresses, exchange_rate, total_nodeminutes
from constants import REQUIRED_CONFIRMATIONS, COIN
from digitalocean_custom import calc_node_minutes
from wallet import hash_to_hex

logging.basicConfig(level=logging.INFO)

def check_unprocessed(top_height):
    for tx_hash in unprocessed_txs.members():
        txid = hash_to_hex(tx_hash).decode()
        tx = Tx.tx_from_hex(txs[tx_hash].decode())
        tx_blockchain = get_tx(txid)
        logging.info('Checking %s' % txid)
        if tx_blockchain.block_height == -1:
            continue
        if top_height - tx_blockchain.block_height + 1 >= REQUIRED_CONFIRMATIONS:  # off by one error - if tx in top block that is 1 conf
            unprocessed_txs.remove(tx_hash)
            for out in tx.txs_out:
                address = out.bitcoin_address()
                if address not in all_addresses:
                    continue
                account = Account(addr_to_uid[address])
                satoshis = out.coin_value
                satoshis = int(satoshis / (1 + account.tip.get()))  # scale for tip
                account.total_coins.incr(satoshis)
                node_minutes_d = calc_node_minutes(satoshis, exchange_rate=exchange_rate.get())
                account.total_minutes.incr(node_minutes_d)
                total_nodeminutes.incr(node_minutes_d)
                nodes_recently_updated.append(account.uid)
                account.add_msg('Detected payment via txid: %s' % (txid,))
                account.add_msg('Increased total paid by %.8f to %.8f (considering tip of %d %%)' % (satoshis / COIN, account.total_coins.get() / COIN, account.tip.get() * 100))
                account.add_msg('Increased node life by %d minutes; expiring around %s' % (node_minutes_d, account.get_expiry().isoformat()))

if __name__ == '__main__':
    while True:
        latest_block = get_latest_block()
        best_block_hash = latest_block.hash
        top_height = latest_block.height
        if best_block_hash == last_block_checked.get():
            time.sleep(10)  # only do this at most once per block
            continue
        logging.info('Latest block: %s' % best_block_hash)

        check_unprocessed(top_height)

        last_block_checked.set(best_block_hash)
        logging.info('Checked: %s' % best_block_hash)