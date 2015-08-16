from binascii import hexlify

from pycoin.tx import Tx

from models import unprocessed_txs, txs, all_addresses, addr_to_uid, Account, known_txs
from constants import COIN

def hash_to_hex(h):
    return hexlify(h[::-1])

def process_tx_initial(tx_obj: Tx):
    txid = tx_obj.hash()
    if txid in known_txs:
        return
    known_txs.add(txid)
    unprocessed_txs.add(txid)
    txs[txid] = tx_obj.as_hex()
    for out in tx_obj.txs_out:
        address = out.address()
        if address in all_addresses:
            uid = addr_to_uid[address]
            account = Account(uid)
            account.txs.add(txid)
            account.add_msg('Found tx for %.08f, %s' % (out.coin_value / COIN, txid))

