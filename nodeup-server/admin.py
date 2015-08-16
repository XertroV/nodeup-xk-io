import argparse

from models import ssh_management_key, digitalocean_api_key, xpub

parser = argparse.ArgumentParser()
parser.add_argument('--ssh-management-key', help='Set fingerprint of ssh management key.', type=str, default='')
parser.add_argument('--digitalocean-api-key', help='Set digitalocean api key.', type=str, default='')
parser.add_argument('--xpub', help='Set xpub key', type=str, default='')
args = parser.parse_args()

if args.ssh_management_key != '':
    ssh_management_key.set(args.ssh_management_key)

if args.digitalocean_api_key != '':
    digitalocean_api_key.set(args.digitalocean_api_key)

if args.xpub != '':
    xpub.set(args.xpub)