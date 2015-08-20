#!/usr/bin/env python3

import argparse
import logging

from models import ssh_management_key, vultr_api_key, xpub, Account, nodes_recently_updated, db, ssh_auditor_key, \
    droplets_to_configure, active_servers, droplet_to_uid, all_msgs, twitter_consumer_key, twitter_consumer_secret, \
    twitter_access_secret, twitter_access_token
from handlers import process_uid
from constants import MIN_TIME
from monitor_nodes import process_next_creation, configure_droplet

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument('--ssh-management-key', help='Set fingerprint of ssh management key.', type=str, default='')
parser.add_argument('--ssh-auditor-key', help='Set fingerprint of ssh management key.', type=str, default='')
parser.add_argument('--digitalocean-api-key', help='Set digitalocean api key.', type=str, default='')
parser.add_argument('--xpub', help='Set xpub key', type=str, default='')
parser.add_argument('--test-uid-create-node', help='Provide UID to test node creation', type=str, default='')
parser.add_argument('--msgs-for-uid', help='provide uid get msgs', type=str, default='')
parser.add_argument('--configure-droplet', help='Provide ID of droplet to be configured', type=str, default='')
parser.add_argument('--create-startup-script', help='create a new startup script for nodes on first boot', default='')
parser.add_argument('--show-account', help='provide uid get account deets', type=str, default='')
parser.add_argument('--show-all-active-nodes', help='provide a summary of all active nodes', action='store_true')
parser.add_argument('--show-last-n-msgs', type=int, default=0, help='Show last n msgs (global)')
parser.add_argument('--msg-user-uid', type=str, default='', help='Specify UID to msg (use with --msg-content)')
parser.add_argument('--msg-content', type=str, default='', help='Specify msg content (use with --msg-user-uid)')
parser.add_argument('--server-owner', type=str, default='', help='Get owner of this droplet ID')
parser.add_argument('--twitter-consumer-key', type=str, default='', help='Set twitter consumer key')
parser.add_argument('--twitter-consumer-secret', type=str, default='', help='Set twitter consumer secret')
parser.add_argument('--twitter-access-token', type=str, default='', help='Set twitter access key')
parser.add_argument('--twitter-access-secret', type=str, default='', help='Set twitter access secret')
args = parser.parse_args()

if args.ssh_management_key != '':
    ssh_management_key.set(args.ssh_management_key)

if args.ssh_auditor_key != '':
    ssh_auditor_key.set(args.ssh_auditor_key)

if args.digitalocean_api_key != '':
    vultr_api_key.set(args.digitalocean_api_key)

if args.xpub != '':
    xpub.set(args.xpub)

if args.test_uid_create_node != '':
    uid = process_uid(args.test_uid_create_node)
    account = Account(uid)
    account.node_created.set(False)
    account.unconf_minutes.incr(MIN_TIME + 1)
    nodes_recently_updated.prepend(uid)
    process_next_creation()

if args.msgs_for_uid != '':
    print(Account(process_uid(args.msgs_for_uid)).get_msgs(100000))

if args.configure_droplet != '':
    droplets_to_configure.add(args.configure_droplet, 0)
    configure_droplet(args.configure_droplet)

if args.create_startup_script != '':
    raise Exception('Unimplemented')

if args.show_account != '':
    account = Account(process_uid(args.show_account))
    print(account.pretty_string())

if args.show_all_active_nodes:
    print('%d servers total' % len(active_servers))
    for id in active_servers:
        account = Account(droplet_to_uid[id])
        print(account.pretty_string())

if args.show_last_n_msgs != 0:
    n = args.show_last_n_msgs
    for msg in all_msgs[:n]:
        print(msg)

if args.msg_user_uid != '' and args.msg_content != '':
    account = Account(process_uid(args.msg_user_uid))
    account.add_msg(args.msg_content)

# if args.set_uid_total_minutes_to_zero != '':
#     account = Account(process_uid(args.set_uid_total_minutes_to_zero))
#

if args.server_owner != '':
    account = Account(droplet_to_uid[args.server_owner])
    print(account.pretty_string())

if args.twitter_consumer_key != '':
    twitter_consumer_key.set(args.twitter_consumer_key)
    
if args.twitter_consumer_secret != '':
    twitter_consumer_secret.set(args.twitter_consumer_secret)

if args.twitter_access_token != '':
    twitter_access_token.set(args.twitter_access_token)
    
if args.twitter_access_secret != '':
    twitter_access_secret.set(args.twitter_access_secret)
