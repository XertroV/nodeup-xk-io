#!/usr/bin/env python3

import time
import random
import datetime
import logging
import subprocess
import asyncio

from paramiko.client import SSHClient, AutoAddPolicy, HostKeys
import requests

from models import last_block_checked, unprocessed_txs, Account, addr_to_uid, nodes_recently_updated, ssh_management_key, vultr_api_key, droplet_to_uid, droplets_to_configure, droplet_ips, ssh_auditor_key
from constants import REQUIRED_CONFIRMATIONS, COIN, MIN_TIME
from digitalocean_custom import calc_node_minutes, regions, droplet_creation_json, create_headers

logging.basicConfig(level=logging.INFO)

headers = create_headers(vultr_api_key.get())

def ssh(hostname, username, password, cmd):
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.connect(hostname, username=username, password=password, timeout=3)
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdin, stdout, stderr

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
        res = requests.post("https://api.vultr.com/v1/server/create?api_key=%s" % vultr_api_key.get(),
                            data={"DCID": 1, "VPSPLANID": 87, "OSID": 192, "SSHKEYID": ssh_management_key.get()})
        if res.status_code == 200:  # accepted
            response = res.json()
            subid = response['SUBID']
            logging.info(response)
            account.creation_ts.set(int(time.time()))
            account.droplet_id.set(subid)
            account.node_created.set(True)
            droplets_to_configure.add(subid, account.creation_ts.get())
            droplet_to_uid[subid] = account.uid
            account.add_msg('Node created successfully! Node ID %s' % (account.droplet_id.get(),))
        else:
            logging.error('Node creation failed! Status %d' % res.status_code)
            logging.error(res.content)
            # import pdb; pdb.set_trace()
    else:
        logging.warning('Account already has a node created.')


def configure_droplet(id, servers=None):
    if servers is None:
        servers = requests.get('https://api.vultr.com/v1/server/list?api_key=%s' % vultr_api_key.get()).json()
    account = Account(droplet_to_uid[id])
    logging.info('Configuring %s for %s' % (id, account.uid))
    droplet = servers[id]
    logging.info('Got droplet %s' % repr(droplet))
    ip = droplet['main_ip']
    password = droplet['default_password']
    droplet_ips[id] = ip
    # ssh
    exec = 'curl https://raw.githubusercontent.com/XertroV/nodeup-xk-io/master/nodeInstall.sh  > nodeInstall.sh; bash nodeInstall.sh "%s" "%s" &> ~/installLog'  # this seems to run okay in the background like this :shrug:
    try:
        print('root', password, ip)
        _, stdout, stderr = ssh(ip, 'root', password, exec % (account.name.get(), account.client.get()))
    except Exception as e:
        print(e)
        logging.error('could not configure droplet %s due to %s' % (id, repr(e)))
        return
    print(stdout.read(), stderr.read())
    account.add_msg('Started install script on node %s -- takes about 30 minutes' % id)
    account.add_msg('Droplet IP: %s' % ip)
    droplets_to_configure.remove(id)


@asyncio.coroutine
def process_node_creations():
    while True:
        process_next_creation()
        yield from asyncio.sleep(1)

@asyncio.coroutine
def configure_droplet_loop():
    while True:
        servers = requests.get('https://api.vultr.com/v1/server/list?api_key=%s' % vultr_api_key.get()).json()
        for droplet_id, ts in droplets_to_configure:
            subid = droplet_id.decode()
            if subid in servers and servers[subid]['server_state'] == 'ok':
                configure_droplet(subid, servers)
            yield from asyncio.sleep(1)  # give other things a chance every once and a while
        yield from asyncio.sleep(60)



if __name__ == '__main__':
    asyncio.async(process_node_creations())
    asyncio.async(configure_droplet_loop())
    asyncio.get_event_loop().run_forever()



