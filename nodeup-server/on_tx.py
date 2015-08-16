import argparse
import json
import sys

from bitcoinrpc import connect_to_local

from models import txs, known_txs, unprocessed_txs, addr_to_uid, Account

parser = argparse.ArgumentParser()
parser.add_argument('--txid')
args = parser.parse_args()

txid = args.txid
known_tx = True if known_txs.add(txid) == 0 else False
if known_tx:
    sys.exit()

bitcoind = connect_to_local()
tx_json = bitcoind.gettransaction(txid)
if tx_json['amount'] <= 0:  # (so it was a send or move)
    sys.exit()

unprocessed_txs.add(txid)
txs[txid] = json.dumps(tx_json)
for detail in tx_json['details']:
    if detail['category'] == 'receive':
        uid = addr_to_uid[detail['address']]
        Account(uid).txs.add(txid)
