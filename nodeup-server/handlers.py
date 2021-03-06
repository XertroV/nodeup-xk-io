import tornado.web
from binascii import hexlify, unhexlify
import os
import hashlib
import simplejson as json

from models import node_accounts, total_nodeminutes, db, Account, exchange_rate, droplets_to_configure, active_servers, node_creation_issues
from digitalocean_custom import actually_charge
from constants import NODE_DETAILS_EMAIL

with open('static/index.html') as f:
    index_file = f.read()

def process_uid(uid):
    return hexlify(hashlib.sha256(uid.encode()).digest())

def handle(method, **params):
    response = {}
    real_uid = params['uid']
    uid = process_uid(params['uid'])  # not user chosen any longer
    account = Account(uid)
    fieldMap = {
        'emailNotify': account.email_notify,
        'email': account.email,
        'name': account.name,
        'client': account.client,
        'tip': account.tip,
        'branch': account.branch,
    }

    if method == 'getPaymentDetails':
        client = params['client']
        months = max(0, int(params['months']))
        tip = account.tip.get()

        amount = actually_charge(months, tip, exchange_rate.get())
        # note: this URI cannot contain spaces as some wallets cannot read it.
        response['uri'] = "bitcoin:%s?amount=%.8f&label=nodeup.xk.io_sponsored_node_funding_address" % (account.address, amount)
        response['status'] = 'Payment received.' if account.unconf_minutes.get() > 0 else 'Waiting for payment...'

    elif method == '':
        pass

    elif method == 'saveField':
        field = params['field']
        value = params['value']
        if field == 'name' and len(value) > 140:
            value = value[:140]
        fieldMap[field].set(value)

    elif method == 'loadField':
        field = params['field']
        response['field'] = field
        response['value'] = fieldMap[field].get()

    elif method == 'getMsgs':
        if 'n' in params:
            n = params['n']
        else:
            n = 10
        response['msgs'] = account.get_msgs(n)

    elif method == 'getStats':
        response['nodeMinutes'] = int(total_nodeminutes.get())
        response['totalMinutesPaid'] = account.total_minutes.get()
        response['totalCoinsPaid'] = account.total_coins.get()
        response['exchangeRate'] = exchange_rate.get()
        response['activeNodes'] = len(active_servers)
        response['nodeCreationIssues'] = node_creation_issues.get()

    elif method == 'recompile':
        if account.node_created.get():
            droplets_to_configure.add(account.droplet_id.get(), 0)
            account.add_msg('Queued node for recompilation.')
            response['recompile_queued'] = True
        else:
            response['recompile_queued'] = False

    elif method == 'sendNodeDetails':
        account.email_user('Node Details', NODE_DETAILS_EMAIL.format(uid=real_uid), force=True)

    return response


class RandomRedirectHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/' + hashlib.sha256(os.urandom(32)).hexdigest()[:40])

class UserHandler(tornado.web.RequestHandler):
    def get(self, uid):
        uid = process_uid(uid)
        if uid not in node_accounts:
            node_accounts.add(uid)

        with open('static/index.html') as f:
            index_file = f.read()
        self.write(index_file)

class APIHandler(tornado.web.RequestHandler):
    def post(self):
        user_json = json.loads(self.request.body.decode())
        response = {}

        if 'method' not in user_json:
            response['error'] = 'no method'
        elif 'params' not in user_json or type(user_json['params']) != dict:
            response['error'] = 'no params or not a dict %s' % user_json['params']
        else:
            method = user_json['method']
            response = handle(method, **user_json['params'])

        self.add_header('content-type', 'application/json')
        self.write(json.dumps(response))


















