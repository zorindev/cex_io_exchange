'''
Created on Dec 3, 2017

@author: zorindev
'''

import sys
import os
import eventlet
if "pydev" not in sys.argv:
    eventlet.monkey_patch()

import json
import logging
import urllib
import urllib2    
import hmac
import hashlib
import time

from config import *
from samples import samples

import random


class CEXIO_Adapter(object):
    """
    converts api payload formats
    """
    
    def __init__(self, username = "", api_key = "", api_secret = "", sleep_period = 1, client = None):
        """
        init
        """
        
        self.username = username
        self.api_key = api_key
        self.api_secret = api_secret
        self.last_nonce = None
        
        self.sleep_period = sleep_period

        self.client = client
        self.logger = client.container.logger
        
    
    def convert_pair(self, pair):
        """
        converts pair
        """
        
        return pair
    
    
    def nonce_is_unique(self, nonce):
        """
        validates if the nonce is unique
        """
        
        if self.client:
            nonce_record = self.client.db.query(sql_get_unique_nonce % (self.client.exchange, str(nonce)), describe = True)[0]
            
            if nonce_record['count'] == 0:
                self.client.db.query(sql_set_unique_nonce % (self.client.exchange, str(nonce)))
                return True
            
            else:
                return False
            
        else:
            raise Exception("Client was not initialized in " + self.__class__.__name__)
            
        
        
    
    
    def set_nonce(self):
        """
        gets nonce value
        initial nonce value is persisted in tbl
        """
        
        nonce = None
        while True:
            nonce = '{:.10f}'.format(time.time() * 1000).split('.')[0]
            nonce = int(nonce)
            nonce += int(1000 * round(random.uniform(1, 10), 4))
            nonce = str(nonce)
            
            if self.nonce_is_unique(nonce):# and nonce != self.last_nonce or self.last_nonce == None:
                break
        
        self.last_nonce = nonce
    
    
    def signature(self):
        """
        get signature
        """
        
        self.set_nonce()
        string = self.last_nonce + str(self.username) + str(self.api_key)
        signature = hmac.new(self.api_secret, string, digestmod=hashlib.sha256).hexdigest().upper()
        return signature

    
    def post(self, url, private, param, user_agent, username):
        """
        post request
        """
        page = {}
        
        if test == "on":
            
            try:
                if "place_order" in url:
                    if param['type'] == "buy":
                        page = samples[url][0]
                    else:
                        page = samples[url][1]
                elif "get_order" in url:
                    page = samples[url][param['id']]
                else:
                    page = samples[url]
            except Exception, e :
                print str(e)
                page = {}
            
        else:
            
            if private == 1:
                param.update({
                    'key': self.api_key,
                    'signature': self.signature(),
                    'nonce': self.last_nonce})
                
            try:
                print "POST ATTEMPT 1: url = ", url
                params = urllib.urlencode(param)
                req = urllib2.Request(url, params, {'User-agent': user_agent + username})
                page = urllib2.urlopen(req).read()
                
            except Exception as e:
                eventlet.sleep(self.sleep_period)
                
                print "POST ATTEMPT 1: url = ", url
                try:
                    params = urllib.urlencode(param)
                    req = urllib2.Request(url, params, {'User-agent': user_agent + username})
                    page = urllib2.urlopen(req).read()
                    
                except Exception, e2:
                    eventlet.sleep(self.sleep_period)
                
                    print "POST ATTEMPT 1: url = ", url
                    # the last exception will be caught in the upstream code
                    params = urllib.urlencode(param)
                    req = urllib2.Request(url, params, {'User-agent': user_agent + username})
                    page = urllib2.urlopen(req).read()
             
        if test == "off":
            f = open(url.replace(":", "_").replace("/", "_").replace("?", "").replace("=", "").replace("&", ""), 'a')
            f.write(url + "\n")
            f.write(page)
            f.write("====\n\n")
            f.close()
        
        if self.logger:
            self.logger.info(url + ": \n" + page + "\n")
        
        return page
    
    
    def convert_method_trade_history(self, api_trade_history):
        """
        """
        
        return api_trade_history
    
    def convert_method_get_order(self, api_order):
        """
        """
        
        if "id" not in api_order:
            
            if "orderId" in api_order:
                api_order['id'] = api_order['orderId']
                api_order.pop("orderId")
            elif "orderID" in  api_order:
                api_order['id'] = api_order['orderID']
                api_order.pop("orderID")
            
        return api_order
    
    def convert_method_cancel_order(self, api_cancel_order_request):
        """
        """
        
        return api_cancel_order_request
    
    def convert_method_currency_limits(self, api_method_currency_limits):
        """
        """
        
        return api_method_currency_limits
    
    
    def convert_method_ticker(self, api_ticker):
        """
        """
        
        return api_ticker
    
    def convert_method_place_order(self, api_place_order_response):
        """
        """
        
        api_place_order_response = json.loads(api_place_order_response)
        try:
            if "time" in api_place_order_response:
                order_time = str(api_place_order_response['time'])
                if len(order_time) > 10:
                    api_place_order_response['time'] = long(order_time[:10]) 
        except Exception, e:
            print e
            
        return json.dumps(api_place_order_response)
    
    def convert_method_order_book(self, api_order_book):
        """
        """
        
        return api_order_book
    
    def convert_method_balance(self, api_balance):
        """
        """
        
        return api_balance
    
    def params_submit_new_order(self, order_type = "buy", bid_price = 0.0, amount = 0.0):
        """
        gets submit order params for cex.io
        """
        
        params = {"type": order_type, "amount": amount, "price": bid_price}
        return params
    
    def params_get_order_status_from_exchange(self, id = ''):
        """
        get order status from exchange
        """
        
        params = {}
        if id:
            params = {"id": id}
            
        return params
    
    def params_cancel_order(self, order_id = None):
        """
        get params for cancel order
        """
        
        params = {}
        if order_id:
            params = {"id": order_id}
            
        return params
    
    
    
    
    