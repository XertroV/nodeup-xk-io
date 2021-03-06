from binascii import hexlify
import logging

from pycoin.tx import Tx

from models import unprocessed_txs, txs, all_addresses, addr_to_uid, Account, known_txs, exchange_rate, nodes_recently_updated
from constants import COIN
from digitalocean_custom import calc_node_minutes

def hash_to_hex(h):
    return hexlify(h[::-1])

def process_tx_initial(tx_obj: Tx):
    found_relevant_address = False
    for out in tx_obj.txs_out:
        address = out.bitcoin_address()
        if address in all_addresses:
            found_relevant_address = True
            break
    if not found_relevant_address:
        logging.info('Found irrelevant tx %s' % hash_to_hex(tx_obj.hash()))
        return

    tx_hash = tx_obj.hash()
    txid = hash_to_hex(tx_hash).decode()
    if tx_hash in known_txs:
        return
    known_txs.add(tx_hash)
    txs[tx_hash] = tx_obj.as_hex()
    for out in tx_obj.txs_out:
        address = out.bitcoin_address()
        if address in all_addresses and address is not None:
            unprocessed_txs.add(tx_hash)
            uid = addr_to_uid[address]
            account = Account(uid)
            account.txs.add(tx_hash)
            account.unconf_minutes.incr(calc_node_minutes(satoshi_amount=out.coin_value, exchange_rate=exchange_rate.get()))
            account.add_msg('Found tx for %.08f, %s' % (out.coin_value / COIN, txid))
            nodes_recently_updated.append(account.uid)

