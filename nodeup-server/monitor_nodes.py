#!/usr/bin/env python3

import time
import random
import datetime
import logging
import subprocess
import asyncio
import socket

from paramiko.client import SSHClient, AutoAddPolicy, HostKeys
import requests

from models import currently_compiling, Account, nodes_recently_updated, ssh_management_key, vultr_api_key, droplet_to_uid, droplets_to_configure, droplet_ips, nodes_currently_syncing, active_servers, tweet_queue, total_nodeminutes, node_creation_issues
from constants import REQUIRED_CONFIRMATIONS, COIN, MIN_TIME, MINUTES_IN_MONTH
from digitalocean_custom import calc_node_minutes, regions, droplet_creation_json, create_headers, actually_charge

logging.basicConfig(level=logging.INFO)

headers = create_headers(vultr_api_key.get())

NODE_CREATION_LIMIT_MSG = b'Server add failed: You have reached the maximum number of active virtual machines for this account. For security reasons, please contact our support team to have the limit raised'


def get_servers():
    return requests.get('https://api.vultr.com/v1/server/list?api_key=%s' % vultr_api_key.get()).json()


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
            account.add_msg('Node creation failed! A minimum of %d minutes need to be purchased at a time. You need %d more minutes.' % (MIN_TIME, MIN_TIME - account.unconf_minutes.get()))
            return
        if account.destroyed.get():
            account.add_msg('Node creation failed as it has already been destroyed, please use a new account and contact nodeup@xk.io to get your coins back.')
            return
        account.add_msg('Creating server now. ETA 10-20 minutes.')
        dcid = random.choice([1, 5, 7])  # NJ, LA, Amsterdam

        try:
            res = requests.post("https://api.vultr.com/v1/server/create?api_key=%s" % vultr_api_key.get(),
                                data={"DCID": dcid, "VPSPLANID": 87, "OSID": 192, "SSHKEYID": ssh_management_key.get(),
                                      "label": str(account.uid), "enable_private_network": 'yes',
                                      'enable_ipv6 string': 'yes'})
        except Exception as e:
            nodes_recently_updated.prepend(next_uid)
            logging.error('Attempted to create server / Exception: %s' % repr(e))

        if res.status_code == 200:  # accepted
            response = res.json()
            subid = response['SUBID']
            logging.info(response)
            account.creation_ts.set(int(time.time()))
            account.droplet_id.set(subid)
            account.node_created.set(True)
            account.dcid.set(dcid)
            droplets_to_configure.add(subid, account.creation_ts.get())
            droplet_to_uid[subid] = account.uid
            active_servers.add(subid)
            account.add_msg('Server created successfully! Server ID %s' % (account.droplet_id.get(),))
            account.tweet_creation()
            node_creation_issues.set(False)
        else:
            logging.error('Server creation failed! Status %d' % res.status_code)
            if res.status_code == 412 and res.content == NODE_CREATION_LIMIT_MSG:
                node_creation_issues.set(True)
            logging.error(res.content)
            nodes_recently_updated.append(next_uid)
            account.add_msg('Server creation failed... will keep retrying')
            return 'CREATION_FAILED'
            # import pdb; pdb.set_trace()
    else:
        logging.warning('Account already has a node created.')


def create_install_command(name, client, branch='', rsync_location=''):
    to_run = 'curl https://raw.githubusercontent.com/XertroV/nodeup-xk-io/master/nodeInstall.sh  > nodeInstall.sh; bash nodeInstall.sh "%s" "%s" "%s" "%s" &> ~/installLog &'
    return to_run % (name, client, branch, rsync_location)


def gen_loc(dcid: int):
    return 'rsync://source-%d.xk.io/bitcoin/' % dcid


def configure_droplet(id, servers=None):
    # presumably id was just popped from droplets_to_configure
    if servers is None:
        servers = get_servers()
    account = Account(droplet_to_uid[id])
    logging.info('Configuring %s for %s' % (id, account.uid))
    droplet = servers[id]
    logging.info('Got server %s' % repr(droplet))
    ip = droplet['main_ip']
    password = droplet['default_password']
    droplet_ips[id] = ip
    # ssh
    try:
        print('root', password, ip)
        _, stdout, stderr = ssh(ip, 'root', password, create_install_command(account.name.get(), account.client.get(), account.branch.get(), gen_loc(account.dcid.get())))
    except Exception as e:
        print(e)
        logging.error('could not configure server %s due to %s' % (id, repr(e)))
        return
    print(stdout.read(), stderr.read())
    account.add_msg('Started compilation script on server %s -- takes about 30 minutes' % id)
    logging.info('Configuring server %s' % id)
    account.compile_ts.set(int(time.time()))
    droplets_to_configure.remove(id)
    currently_compiling.add(id)


def check_compiling_node(id):
    account = Account(droplet_to_uid[id])
    ip = droplet_ips[id].decode()
    s = socket.socket()
    try:
        s.connect((ip, 8333))  # VEEERRRRY simple
    except:
        # can't connect, check we're not way out in terms of time
        if int(time.time()) - account.compile_ts.get() > 60 * 60:  # 60 min
            account.add_msg('Possible compile issue (taking >60 minutes). Restarting.')
            droplets_to_configure.add(id, 0)
            currently_compiling.remove(id)
        return
    s.close()
    account.add_msg('Node detected! Check at https://getaddr.bitnodes.io/nodes/%s-%d/' % (ip, 8333))
    account.email_node_up(ip)
    logging.info('Detected node %s' % id)
    currently_compiling.remove(id)
    nodes_currently_syncing.add(id)


def check_server_for_expiration(id):
    account = Account(droplet_to_uid[id])
    now = int(time.time())
    creation_ts = account.creation_ts.get()
    paid_minutes = account.total_minutes.get()
    #if (now) < (creation_ts + MIN_TIME * 60):  # created in within the last MIN_TIME
    #    return
    if now > (creation_ts + paid_minutes * 60):
        # then destroy
        logging.warning('Destroying node %s' % id)
        res = requests.post("https://api.vultr.com/v1/server/destroy?api_key=%s" % vultr_api_key.get(),
                            data={"SUBID": int(id)})
        if res.status_code == 200:
            account.destroy()
            account.add_msg('Node lifetime consumed in total, node destroyed.')
        else:
            logging.error('Could not destroy server! %s' % id)
            account.add_msg('Attempted to destroy node (unpaid into future) but I failed :(')
        if account.destroyed.get():
            active_servers.remove(id)


@asyncio.coroutine
def process_node_creations(stop_at):
    while time.time() < stop_at:
        response = process_next_creation()
        if response == 'CREATION_FAILED':
            yield from asyncio.sleep(300)
        yield from asyncio.sleep(1)


@asyncio.coroutine
def configure_droplet_loop(stop_at):
    while time.time() < stop_at:
        servers = get_servers()
        for droplet_id, ts in droplets_to_configure:
            subid = droplet_id.decode()
            if subid in servers and servers[subid]['server_state'] == 'ok':
                configure_droplet(subid, servers)
            yield from asyncio.sleep(1)  # give other things a chance every once and a while
        yield from asyncio.sleep(60)


@asyncio.coroutine
def check_compiling_loop(stop_at):
    while time.time() < stop_at:
        for id in currently_compiling.members():
            check_compiling_node(id)
            yield from asyncio.sleep(1)
        yield from asyncio.sleep(60)


@asyncio.coroutine
def destroy_unpaid_loop(stop_at):
    while time.time() < stop_at:
        for id in active_servers.members():
            check_server_for_expiration(id)
            yield from asyncio.sleep(1)
        yield from asyncio.sleep(600)


if __name__ == '__main__':
    def main():
        now = int(time.time())
        stop_at = now + 60 * 60 * 4  # 4 hours from now
        asyncio.async(process_node_creations(stop_at))
        asyncio.async(configure_droplet_loop(stop_at))
        asyncio.async(check_compiling_loop(stop_at))
        asyncio.async(destroy_unpaid_loop(stop_at))
        pending = asyncio.Task.all_tasks()
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*pending))
    main()



