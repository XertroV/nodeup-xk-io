#!/usr/bin/env python3

import time
import random
import datetime
import logging
import subprocess
import asyncio


import requests

from models import last_block_checked, unprocessed_txs, Account, addr_to_uid, nodes_recently_updated, ssh_management_key, digitalocean_api_key, droplet_to_uid, droplets_to_configure, droplet_ips
from constants import REQUIRED_CONFIRMATIONS, COIN, MIN_TIME
from digitalocean import calc_node_minutes, regions, droplet_creation_json, create_headers

headers = create_headers(digitalocean_api_key.get())

def process_next_creation():
    if len(nodes_recently_updated) == 0:
        return
    next_uid = nodes_recently_updated.popleft()
    logging.info("Processing uid: %s" % next_uid)
    account = Account(next_uid)
    if not account.node_created.get():
        if account.unconf_minutes.get() < MIN_TIME:
            account.add_msg('Node creation failed! A minimum of %d minutes need to be purchased at a time. You need %d more minutes.' % (MIN_TIME, MIN_TIME - account.total_minutes))
            return
        account.add_msg('Creating node now.')
        creation_request = droplet_creation_json(account.uid, ssh_fingerprints=[ssh_management_key.get()])
        res = requests.post("https://api.digitalocean.com/v2/droplets", json=creation_request, headers=headers)
        if res.status_code == 202:  # accepted
            response = res.json()
            created_at = datetime.datetime.strptime(response['droplet']['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            account.creation_ts.set(created_at.timestamp())
            account.droplet_id.set(response['droplet']['id'])
            account.node_created.set(True)
            droplets_to_configure.add(response['droplet']['id'])
            droplet_to_uid[response['droplet']['id']] = account.uid
            account.add_msg('Node created successfully! Node ID %s' % (account.droplet_id.get(),))
        else:
            logging.error('Node creation failed! Status %d' % res.status_code)
            logging.error(res)
            # import pdb; pdb.set_trace()
    else:
        logging.warning('Account already has a node created.')


def configure_droplet(id, ts):
        droplet_res = requests.get('https://api.digitalocean.com/v2/droplets/%s' % id, headers=headers)
        if droplet_res.status_code == 200:
            account = Account(droplet_to_uid[id])
            droplet = droplet_res.json()
            droplet_ips[id] = droplet['networks']['v4'][0]['ip_address']
            ip = droplet['networks']['v4'][0]['ip_address']
            # test if sshable
            proc = subprocess.Popen(['ssh', 'root@%s' % ip, 'wget https://raw.githubusercontent.com/XertroV/nodeup-xk-io/master/nodeInstall.sh && screen -mdS bi bash nodeInstaller.sh "%s" "%s"' % (account.name.get(), account.client.get())],
                                    stdin=subprocess.PIPE)
            proc.communicate(file_contents)
            if proc.retcode != 0:
                account.add_msg('Droplet IP: %s' % ip)
                droplets_to_configure.remove(next_droplet_id)
        else:
            logging.error('Could not access node with id %d' % id)


@asyncio.coroutine
def process_node_creations():
    while True:
        process_next_creation()
        yield from asyncio.sleep(1)

@asyncio.coroutine
def configure_droplet_loop():
    while True:
        for droplet_id, ts in droplets_to_configure:
            configure_droplet(droplet_id, ts)
            yield from asyncio.sleep(1)  # give other things a chance every once and a while
        yield from asyncio.sleep(60)



if __name__ == '__main__':
    while True:
        if len(nodes_recently_updated) == 0 and len(droplets_to_configure) == 0:
            print('sleeping')
            time.sleep(10)
            continue
        process_next_creation()
        configure_next_node()



