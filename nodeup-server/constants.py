REQUIRED_CONFIRMATIONS = 2
COIN = 10 ** 8
MIN_TIME = 60 * 24 * 14 - 1  # min 14 days
MINUTES_IN_MONTH = 60 * 24 * 30

EMAIL_FOOTER = """
Thanks for using NodeUp.xk.io!

Cheers,
Max

PS. If you have any queries you can reply to this email.
"""

NODE_UP_EMAIL = """Hi,

Your new node has been created and you can follow it's
synchronisation over at https://getaddr.bitnodes.io/nodes/{ip}-8333/.
""" + EMAIL_FOOTER

NODE_DETAILS_EMAIL = """Hi,

The management URL for your node is: http://nodeup.xk.io/{uid}
""" + EMAIL_FOOTER

NODE_DESTROYED_EMAIL = """Hi,

Your node at NodeUp.xk.io has been decommissioned as it's account has run dry.
If you would like to sponsor a new node please use a new account.
""" + EMAIL_FOOTER