import random

from constants import COIN

DOLLARS_PER_MONTH = 5.0
MINUTES_PER_MONTH = 30 * 24 * 60
regions = ['nyc3', 'nyc2']

def calculate_cost_in_dollars(months):
    return months * DOLLARS_PER_MONTH

def actually_charge(months, tip, exchange_rate=1.0):
    return calculate_cost_in_dollars(months) * (1 + tip) / exchange_rate

def calc_node_minutes(satoshi_amount=None, dollar_amount=None, exchange_rate=1.0):
    if (satoshi_amount is None and dollar_amount is None) or (satoshi_amount is not None and dollar_amount is not None):
        raise AttributeError('Exactly one of satoshi_amount or dollar_amount is needed')
    if satoshi_amount is not None:
        coins = satoshi_amount / COIN
        dollars = exchange_rate * coins
    else:
        dollars = dollar_amount
    return int(dollars / DOLLARS_PER_MONTH * MINUTES_PER_MONTH)


def droplet_creation_json(uid, rand_region=False, ssh_fingerprints=None):
    region = 'nyc3' if not rand_region else random.choice(regions)
    keys = None if ssh_fingerprints is None else ssh_fingerprints
    r = {
      "name": uid.decode(),
      "region": region,
      "size": "512mb",
      "image": 13163861,
      "ssh_keys": keys,
      "backups": False,
      "ipv6": True,
      "user_data": None,
      "private_networking": None
    }
    print(r)
    return r


def create_headers(api_key):
    r = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer %s' % api_key,
    }
    return r