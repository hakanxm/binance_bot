# utils.py

import hmac
import hashlib
from urllib.parse import urlencode
from config import API_SECRET

def sign(params):
    query_string = urlencode(params)
    return hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
