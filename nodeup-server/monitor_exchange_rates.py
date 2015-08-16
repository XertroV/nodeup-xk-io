#!/usr/bin/env python3

import time

import requests

from models import exchange_rate

while True:
    res = requests.get('https://bitpay.com/api/rates/usd')
    response = res.json()
    if 'code' in response:
        if response['code'] == "USD":
            exchange_rate.set(response['rate'])
    time.sleep(30)