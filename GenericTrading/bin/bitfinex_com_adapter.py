'''
Created on Dec 3, 2017

@author: zorindev
'''

import time
import json
import base64
import hmac
import hashlib
import requests

"""

adapter notes:

    cex.io
    {
        u'date': u'1512566262', 
        u'tid': u'457756', 
        u'amount': u'1.00000000', 
        u'type': u'sell', 
        u'price': u'0.03463904'
    }, 
    
    bitfinex: [107285475,1512323775260,3.30249543,0.003286]
    {
        u'date': u'1512323775260',
        u'tid': u'107285475',
        u'amount': u'3.30249543', 
        u'type': u'buy', 
        u'price': u'0.003286'
    }
    
    
    
    
    

    def _sign_payload(self, payload):
        j = json.dumps(payload)
        data = base64.standard_b64encode(j.encode('utf8'))

        h = hmac.new(self.SECRET.encode('utf8'), data, hashlib.sha384)
        signature = h.hexdigest()
        return {
            "X-BFX-APIKEY": self.KEY,
            "X-BFX-SIGNATURE": signature,
            "X-BFX-PAYLOAD": data
        }

    

"""


class BITFINEX_Adapter(object):
    """
    converts api payload formats
    """
    
    
    def __init__(self, username, api_key, api_secret):
        """
        init
        """
        
        self.username = username
        self.api_key = api_key
        self.api_secret = api_secret
        self.last_nonce = None
    
    def convert_pair(self, pair):
        """
        converts pair
        """
        
        if pair:
            return pair.lower().replace("/", "")
        else:
            return ""
    
    
    @property
    def set_nonce(self):
        """
        sets nonce
        """
        
        nonce = None
        while True:
            nonce = str(time.time() * 1000000)
            if nonce != self.last_nonce or self.last_nonce == None:
                break
        
        self.last_nonce = nonce
        return self.last_nonce
        
        
    def signature(self, payload = ""):
        """
        sign payload
        """
        
        j = json.dumps(payload)
        data = base64.standard_b64encode(j.encode('utf8'))

        h = hmac.new(self.api_secret.encode('utf8'), data, hashlib.sha384)
        return {
            "X-BFX-APIKEY": self.api_key,
            "X-BFX-SIGNATURE": h.hexdigest(),
            "X-BFX-PAYLOAD": data
        }
    
    def config_params(self, url, params):
        """
        configures parameters
        """
        
        params['nonce'] = self.set_nonce
        return params
    
    def post(self, url = "", private = False, param = {}, user_agent = "", username = ""):
        """
        post to bitfinex
        """

        json_resp = {}
        try:
            if(private):
                param = self.config_params(url, param)
                r = requests.post(url, headers = self.signature(param), verify=True)
            else:
                r = requests.request("GET", url)
                
            json_resp = r.json()
        except Exception, e:
            print("post exception: ", str(e))

        return json_resp
    
    
    def convert_method_trade_history(self, api_trade_history):
        """
        bitfinex trade history
        """
        pass
        #rtn = {}
        #for entry in api_trade_history:
            
        #return api_trade_history
    
    def convert_method_get_order(self, api_order):
        """
        """
        
        return api_order
    
    def convert_method_cancel_order(self, api_cancel_order_request):
        """
        """
        
        return api_cancel_order_request
    
    
    def convert_method_ticker(self, api_ticker):
        """
        """
        
        return api_ticker
    
    def convert_method_place_order(self, api_place_order_request):
        """
        """
        
        return api_place_order_request
    
    def convert_method_order_book(self, api_order_book):
        """
        """
        
        return api_order_book
    
    def convert_method_balance(self, api_balance):
        """
        """
        
        return api_balance
    
    
    
    
    