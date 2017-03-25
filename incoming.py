"""
GCMS

(c) 2017 Alpeware LLC
"""
import config
import httplib2
import logging
import re
import string
import webapp2

from urllib import urlencode
from google.appengine.api import taskqueue
from google.appengine.api import memcache
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

NAME_RE = r'([^<]+)'
EMAIL_RE = r'[^<]+<([^>]+)'

def send_message(sender, recipient, subject, text):
    http = httplib2.Http()
    http.add_credentials('api', config.MAILGUN_API_KEY)

    url = 'https://api.mailgun.net/v3/{}/messages'.format(config.MAILGUN_DOMAIN_NAME)
    data = {
        'from': 'Alpeware Newsletter <{}>'.format(sender),
        'to': recipient,
        'subject': subject,
        'text': text 
        }

    resp, content = http.request(
        url, 'POST', urlencode(data),
        headers={"Content-Type": "application/x-www-form-urlencoded"})

    if resp.status != 200:
        raise RuntimeError(
            'Mailgun API error: {} {}'.format(resp.status, content))

def subscribe(email_address=None, name=None):
    logging.info('subscribing %s to newsletter', email_address)
    http = httplib2.Http()
    http.add_credentials('api', config.MAILGUN_API_KEY)

    url = 'https://api.mailgun.net/v3/lists/%s/members' % (config.MAILING_LIST)
    data = {
        'address': email_address,
        'subscribed': True,
        'upsert': True
    }

    resp, content = http.request(
        url, 'POST', urlencode(data),
        headers={"Content-Type": "application/x-www-form-urlencoded"})

    if resp.status != 200:
        raise RuntimeError(
            'Mailgun API error: {} {}'.format(resp, content))
    send_message(config.UNSUBSCRIBE_EMAIL, email_address, config.NEWSLETTER_SUB_SUBJECT, config.NEWSLETTER_WELCOME)


def unsubscribe(email_address=None):
    logging.info('unsubscribing %s to newsletter', email_address)
    http = httplib2.Http()
    http.add_credentials('api', config.MAILGUN_API_KEY)

    url = 'https://api.mailgun.net/v3/lists/%s/members/%s' % (config.MAILING_LIST, email_address)
    resp, content = http.request(
        url, method='DELETE',
        headers={"Content-Type": "application/x-www-form-urlencoded"})

    if resp.status != 200:
        raise RuntimeError(
            'Mailgun API error: {} {}'.format(resp, content))
    send_message(config.SUBSCRIBE_EMAIL, email_address, config.NEWSLETTER_UNSUB_SUBJECT, config.NEWSLETTER_GOODBYE)


class MailHandler(InboundMailHandler):
    def receive(self, mail_message):

        email_address = mail_message.sender
        name_match = re.search(NAME_RE, mail_message.sender)
        name = ''
        if name_match:
            name = name_match.group(1)
            email_address = re.search(EMAIL_RE, mail_message.sender).group(1)

        logging.info('name: %s', name)

        if 'unsubscribe@' in mail_message.to:
            return unsubscribe(email_address)
        elif 'subscribe@' in mail_message.to:
            return subscribe(mail_message.sender)

        logging.info("Received a message from: " + mail_message.sender)
        logging.info("Sent to: " + mail_message.to)
        plaintext_bodies = mail_message.bodies('text/plain')
        for content_type, body in plaintext_bodies:
            plaintext = body.decode()
            logging.info("Plain text body of length %d.", len(plaintext))

app = webapp2.WSGIApplication([
    MailHandler.mapping()
], debug=True)
