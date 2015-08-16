#!/usr/bin/env python3

import time
import random
import datetime
import logging

import requests

from models import last_block_checked, unprocessed_txs, Account, addr_to_uid, nodes_recently_updated, ssh_management_key, digitalocean_api_key
from constants import REQUIRED_CONFIRMATIONS, COIN, MIN_TIME
from digitalocean import calc_node_minutes, regions, droplet_creation_json, create_headers




while True:
    if len(nodes_recently_updated) == 0:
        time.sleep(10)
        continue
    next_uid = nodes_recently_updated.popleft()
    account = Account(next_uid)
    if not account.node_created.get():
        if account.unconf_minutes.get() < MIN_TIME:
            account.add_msg('Node creation failed! A minimum of %d minutes need to be purchased at a time. You need %d more minutes.' % (MIN_TIME, MIN_TIME - account.total_minutes))
            continue
        creation_request = droplet_creation_json(account.uid, ssh_fingerprints=[ssh_management_key.get()])
        headers = create_headers(digitalocean_api_key.get())
        res = requests.post("https://api.digitalocean.com/v2/droplets", json=creation_request, headers=headers)
        if res.status_code == 202:  # accepted
            response = res.json()
            created_at = datetime.datetime.strptime(response['droplet']['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            account.creation_ts.set(created_at.timestamp())
            account.droplet_id.set(response['droplet']['id'])
            account.node_created.set(True)
            account.add_msg('Node created successfully! Node ID %s' % (account.droplet_id.get(),))
        else:
            logging.error('Node creation failed! Status %d' % res.status_code)
            logging.error(res)
            # import pdb; pdb.set_trace()

