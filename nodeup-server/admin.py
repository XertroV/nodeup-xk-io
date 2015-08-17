import argparse
import logging

from models import ssh_management_key, vultr_api_key, xpub, Account, nodes_recently_updated, db, ssh_auditor_key, droplets_to_configure
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
parser.add_argument('--create-startup-script', help='create a new startup script for nodes on first boot')
parser.add_argument('--show-account', help='provide uid get account deets', type=str)
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
    import pdb; pdb.set_trace()