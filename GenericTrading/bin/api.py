'''
Created on Nov 7, 2017

@author: zorindev
'''

import sys
import os
import eventlet
if "pydev" not in sys.argv:
    eventlet.monkey_patch()

import importlib
import json

from util import *
from config import *
from db import *
from samples import *

from flask_socketio import emit

from config import *
from pprint import *

class API(object):
    
    username = None
    api_key = None
    secret = None
    
    sleep_period = None

    db = None
    
    def __init__(self, exchange = "", ex_username = "", ex_api_key = "", ex_api_secret = "", client = None):
        """
        init
        """
        
        self.client = client
        self.exchange = exchange
        self.last_nonce = None
        self.username = str(ex_username);
        self.api_key = str(ex_api_key);
        self.api_secret = str(ex_api_secret);
        self.load_exchange_params()
        
        self.calculate_sleep_period()
        
        if self.client.init:
            adapter_class = getattr(importlib.import_module(self.adapter_module_name), self.adapter_class_name)
            self.adapter = adapter_class(
                self.username, 
                self.api_key, 
                self.api_secret, 
                self.sleep_period, 
                self.client
            )
        
        
    def calculate_sleep_period(self):
        """
        increases sleep period based on the number of open markets
        """
        
        count = self.client.db.query(sql_get_open_market_count % (self.exchange), describe = True)
        self.sleep_period = int(api_sleep_period) * int(count[0]['count'])
        
    
    def load_exchange_params(self):
        """
        loads exchange details from db or stops the client
        """
        ex_db_details = self.client.db.query(sql_get_exchange_config % self.exchange, describe = True)
        if len(ex_db_details) == 1:
            for key, value in ex_db_details[0].iteritems():
                setattr(self, key, value)
        else:
            self.client.init = False
        
        
    def api_call_limit_check(self):
        """
        checks the api_call limit
        """
        
        rtn = False
        
        try:
            count = self.client.db.query(sql_check_call_limit % call_volume_limit, describe = False)[0][0]
            if count < call_volume_limit:
                rtn = True
            
            return rtn;
            
        except Exception as e:
            print str(e)
            raise Exception("unable to track API call limit. Exiting ... ")
            emit("ex_notification", {'id': self.container.id, 'msg': str(e)})

        
    
    def wait(self):
        """
        wait for limit 
        """    
        while True:
            if self.api_call_limit_check():
                break
            else:
                eventlet.sleep(self.sleep_period)
            
        
    def persist_call(self):
        """
        writes an entry into the calls table
        """
        self.client.db.query(sql_track_call)
    
        
    def api_call(self, method = "", pair = '', private = False, param = {}):
        """
        calls api: cient passes the column name where the method value is contained
        """
        
        self.wait()
        self.persist_call()
        url = self.api_url + getattr(self, method) + "/" + self.adapter.convert_pair(pair)
            
        answer = getattr(self.adapter, "convert_" + method)(
            self.adapter.post(
                url,
                private, 
                param,
                self.user_agent,
                self.username
            )
        )
            
        try:
            return json.loads(answer)
        except Exception as e:
            print("api_call exception: ", str(e))
            return answer
        
        
    def get_method_params(self, method, **kwargs):
        """
        sends request to adapter to get request parameters
        """
        return getattr(self.adapter, "params_" + method)(**kwargs)
    