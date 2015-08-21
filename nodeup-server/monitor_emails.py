#!/usr/bin/env python3

import smtplib
from email.mime.text import MIMEText
import json
import time
import logging

from models import mandrill_api_key, mandrill_username, email_queue_json

logging.basicConfig(level=logging.INFO)

smtp = smtplib.SMTP('smtp.mandrillapp.com', port=587)
smtp.login(mandrill_username.get(), mandrill_api_key.get())

if __name__ == '__main__':
    while True:
        if len(email_queue_json) > 0:
            orig_msg = email_queue_json.popleft()
            try:
                email = json.loads(orig_msg.decode())
                msg = MIMEText(email['body'])
                msg['Subject'] = email['subject']
                msg['From'] = email['from']
                msg['To'] = email['to']
                smtp.send_message(msg)
            except Exception as e:
                email_queue_json.prepend(orig_msg)
                logging.error(str(e))
                raise e
        time.sleep(1)