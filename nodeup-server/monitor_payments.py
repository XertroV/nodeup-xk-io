import time

from bitcoinrpc import connect_to_local

from models import last_block_checked, unprocessed_txs, Account, addr_to_uid, nodes_recently_updated
from constants import REQUIRED_CONFIRMATIONS, COIN
from digitalocean import calc_node_minutes

bitcoind = connect_to_local()

while True:
    best_block_hash = bitcoind.getbestblockhash()
    if best_block_hash == last_block_checked.get():
        time.sleep(10)
        continue
    last_block_checked.set(best_block_hash)

    for txid in unprocessed_txs.members():
        tx = bitcoind.gettransaction(txid.decode())
        if tx['confirmations'] >= REQUIRED_CONFIRMATIONS:
            unprocessed_txs.remove(txid)
            for detail in tx['details']:
                if detail['category'] == 'receive':
                    address = detail['address']
                    account = Account(addr_to_uid[address])
                    satoshis = int(COIN * detail['amount'])
                    account.total_coins.incr(satoshis)
                    node_minutes_d = calc_node_minutes(satoshis)
                    account.total_minutes.incr(node_minutes_d)
                    account.add_msg('Detected payment via txid: %s' % (tx['txid'],))
                    account.add_msg('Increased total paid by %d to %d' % (detail['amount'], account.total_coins.get() / COIN))
                    account.add_msg('Increased node life by %d minutes; expiring around %d' % (node_minutes_d, account.get_expiry()))
                    nodes_recently_updated.append(account.uid)