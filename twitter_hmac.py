from pprint import pprint
from datetime import datetime
import random
import string
import hashlib
import hmac
import base64
import urllib.parse

TW_CONSUMER_KEY = '3nVuSoBZnx6U4vzUxf5w'
TW_CONSUMER_SECRET = 'Bcs59EFbbsdF6Sl9Ng71smgStWEGwXXKSjYvPVt7qys'


def get_oauth_authorization(oauth_token, oauth_token_secret, method, url,
                            body='', timestamp=None, oauth_nonce=None):
    if not url: return ''

    if timestamp is None:
        timestamp = int(datetime.utcnow().timestamp())
    if oauth_nonce is None:
        oauth_nonce = '0'
        # oauth_nonce = ''.join(random.choices(string.ascii_uppercase + string.digits, k=34))

    method = method.upper()
    parse_url = urllib.parse.urlparse(url)
    link = parse_url.scheme + '://' + parse_url.netloc + parse_url.path
    payload = urllib.parse.parse_qsl(parse_url.query)
    if body:
        payload += urllib.parse.parse_qsl(body)
    payload += [
        ('oauth_version', '1.0'),
        ('oauth_signature_method', 'HMAC-SHA1'),
        ('oauth_consumer_key', TW_CONSUMER_KEY),
        ('oauth_token', oauth_token),
        ('oauth_nonce', oauth_nonce),
        ('oauth_timestamp', str(timestamp))
    ]
    payload.sort(key=lambda x: x[0])
    for_sign = (
        method
        + '&'
        + urllib.parse.quote(link, safe='')
        + '&'
        + urllib.parse.urlencode(payload).replace('+', '%20').replace('%', '%25').replace('=', '%3D').replace('&', '%26')
    )
    sign = hmac.new(
        (
            TW_CONSUMER_SECRET
            + '&'
            + (oauth_token_secret if oauth_token_secret else '')
        ).encode(),
        for_sign.encode(),
        hashlib.sha1
    )
    sign_b64 = base64.b64encode(sign.digest()).decode()
    sign_data = {
        'method': method,
        'url': url,
        'parse_url': parse_url,
        'timestamp': timestamp,
        'oauth_nonce': oauth_nonce,
        'oauth_token': oauth_token,
        'oauth_token_secret': oauth_token_secret,
        'oauth_consumer_key': TW_CONSUMER_KEY,
        'oauth_consumer_secret': TW_CONSUMER_SECRET,
        'payload': payload,
        'sign': sign_b64
    }
    authorization = (
        f'OAuth realm="http://api.twitter.com/", oauth_version="1.0", oauth_token="{sign_data["oauth_token"]}", oauth_nonce="{sign_data["oauth_nonce"]}", oauth_timestamp="{sign_data["timestamp"]}", oauth_signature="{urllib.parse.quote(sign_data["sign"], safe="")}", oauth_consumer_key="{sign_data["oauth_consumer_key"]}", oauth_signature_method="HMAC-SHA1"'
    )
    return sign_data, authorization
