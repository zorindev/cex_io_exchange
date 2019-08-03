

import sys
import os
import eventlet
#from openpyxl.packaging.relationship import Relationship
if "pydev" not in sys.argv:
    eventlet.monkey_patch()

import logging
import sys
from flask_socketio import emit

from threading import Thread, Event
import time

from config import *
from client import *

import linecache


class Ex(object):

    client = None
    
    def __init__(self, id, ws, logger):
        """
        constructor of Ex
        """
        
        self.logger = logger
        
        self.id = id;
        self.ws = ws;
        self.connected = False;
        
        self.ws_identety_key        = ""
        self.exchange               = ""
        self.market                 = ""
        self.username               = ""
        self.api_key                = ""
        self.secret                 = ""
        self.lower_margin_boundary  = 0.00
        self.upper_margin_boundary  = 0.00
        self.profit_margin          = 0.00
        self.min_trade_amount       = 0.00
        self.level_percentage       = 0.00
        self.number_of_levels       = 1
        
        """
        states:  0 = not started
                -1 = request error
                -2 = not stopped
                 1 = statred
                 2 = stopped
                 3 = exec error
        """
        self.state = 0
        self.state_message = ""
        
        self.logger.info("Initializing the client with ID = " + self.id)
        

    def validate_ws_key(self, ws_key):
        """
		TODO
		"""
        return True
        
    def validate_trading_params(self, data):
        """
        validate trading params
        """
        try:
            if int(data[6]) and int(data[7]) and float(data[8]) and float(data[9]) and int(data[10]):
                return True
            else:
                return False
        except Exception as e:
            return False
        
        
    def set_trade_parameters(self, payload):
        """
        parses request and initializes trade parameters
        """

        if payload['id'] == self.id:
            if self.state in (0, -1, -2, 2, 3):
                data = payload['data']
                data = [x for x in data if x]
                
                if data and len(data) == 12 and self.validate_ws_key(data[0]) and self.validate_trading_params(data):
                    self.ws_identity_key        = data[0]
                    self.exchange               = data[1]
                    self.market                 = data[2]
                    self.username               = data[3]
                    self.api_key                = data[4]
                    self.secret                 = data[5]
                    self.lower_margin_boundary  = data[6]
                    self.upper_margin_boundary  = data[7]
                    self.profit_margin          = data[8]
                    self.min_trade_amount       = data[9]
                    self.number_of_levels       = data[10]
                    self.level_percentage       = data[11]
                    
                    self.state = 1
                    self.state_message = "Request validated. Starting trade"
                    
                    self.logger.info("ex.py::set_trade_parameters: payload = " + str(payload))
                    
                else:
                    self.state = -1
                    self.state_message = "Invalid request"
                    
            else:
                self.state_message = "Request could not be started becaue of the state " + str(self.state)
                self.state = -1
                
        else:
            self.state = -1
            self.state_message = "Session with id " + self.id + " does not exist"
            
            
        self.client = Client(
            exchange = self.exchange, 
            market = self.market,
            ex_username = self.username, 
            ex_api_key = self.api_key, 
            ex_api_secret = self.secret, 
            number_of_levels = self.number_of_levels,
            level_percentage = self.level_percentage, 
            lower_margin = self.lower_margin_boundary,
            upper_margin = self.upper_margin_boundary,
            profit_margin = self.profit_margin,
            min_asset_amount = self.min_trade_amount,
            container = self,
            ws = self.ws
        )
        
       
    
    def run_trade(self):
        """
        runs the trade - this methodis called as a background thread
        """
        
        """
        
        leveled trading mechanism state machine:
        
            [0]    set the balance limit for this trading market:
                    limit = balance / (number of markets + 1)
                
            
            set the maximum number of open orders
            
            set the number of fall levels
            
            set the fall margins
            
            set the increment-on-fall percentage
            
            
            [1]    get open order from database, based on exchange and market.
                    if more that one order exists return error to front end for a manual fix [exit] 
                        
                    if open order does not exist then go to [2]
                    
                    if open order does exist then go to [3]
                            
            
            [2]    submit new buy order:
                        get trade history - orders in the last 10 minutes
                        calculate market direction - is market rising or falling based on buy order values in trade_history
                        calculate min and max price
                
                        if decreasing and is below 75% mark from maximum price:
                            get current bids
                            calculate average
                            place order for 0.2 * N at average price
                            persist order and link it to other buy orders as needed and go to [1]
                            
                        if decreasing and is above or at 75% mark from maximum price:
                            go to [1]
                            
                        if increasing and below or at 75% mark to maximum price:
                            get current bids
                            calculate average
                            place order for 0.2 * N at average price
                            persist order and link it to other buy orders as needed and go to [1]
                            
                        if increasing and is above 75% mark from maximum price:
                            go to [1]
                    
            [3]     get market trading window and check order status in API
            
                        if buy order 3.1
                            
                            3.1.1 if not completed and market window has not shifted to lower or upper levels then go to [1]
                            
                            3.1.2 if not completed and market window has shifted to upper level then go to [4]
                       
                            3.1.3 if completed and market window did not shift then go to [5]
               
                            3.1.4 if completed and market window shift to a lower level then go to [6]
                            
                            3.1.5 if completed and market window shifted to upper level then go to [7]
                           
                        if sell order 3.2
                        
                            3.2.1 if not completed and in current market go to [1]
                            
                            3.2.2 if not completed and market had shifted to lower level
                                cancel the sell order
                                persist cancellation in db
                                create a new buy order in db
                                link it this this order and go to [1]
                                
                            3.2.3 if order completed
                                close order in db and go to [1]
                                
               
               
            [4]     cancel this buy order as it is at a lower trading window than the market window
                    persist the status and go to [1]
                    
                    
            [5]     buy order is completed and the market window is current 
                        calculate the assets that need to be sold from this buy order and all the linked buy orders
                        place a sell order at N% profit
                        persist the order in db and go to [1]
                    
            
            [6]    buy order was completed at a higher level market
                        calculate the amount of asset needed to be purchased at current market price for profit combined with asset that was already purchased
                        create a new records in db for a new upcoming order and link the new order to the completed buy order
                        go to [2]
            
            
            [7]    buy order was completed and market had shifted to an upper level
                        so place sell order at the highest asking price
                        persist order in db and go to [1]
                        
                        
                        
            =============================================
            
            
            order states:
                o - opened
                n - cancelled
                c - closed
                a - abandoned
                l - leveled
                
            
        """
        
        self.client.close_market()
        if self.client.init and self.client.is_market_useable():
            
            self.client.reset()
            self.client.open_market()
            
            while self.client.on():
                
                try:
                    
                    self.client.report("Trading of " + self.client.exchange + " " + self.client.market + " is in progress.")
                    db_order = self.client.get_order_details_from_db()
                    
                    # submit new buy order - state 2
                    if len(db_order) == 0:
                        self.client.submit_new_buy_order()
                        
                    # report order state error - exit
                    elif len(db_order) > 1:
                        self.client.report("multiple in_progress orders exist in the market " + self.client.exchange + "::" + self.client.market)
                        self.client.close_market()
                        self.client.off()
                        
                    # manage existing api order - state 3
                    elif len(db_order) == 1:
                        
                        db_order = db_order[0]
                        api_order = self.client.get_order_status_from_exchange(db_order)
                        
                        if api_order and "error" not in api_order and "id" in api_order and "status" in api_order:
                            market_window = self.client.get_market_window(db_order)
                            
                            # REMOVE
                            #market_window = -1
                            #api_order['status'] = 'd'
                            
                            if db_order['type'] == "buy":
                                
                                
                                
                                if api_order['status'] == "cd" or api_order['status'] == "a":
                                    # 3.1
                                    if market_window == 0:
                                        # go to [1]
                                        continue
                                    
                                    # 3.2
                                    elif market_window > 0:
                                        # [4]
                                        
                                        self.client.cancel_order(order_id_type = "buy_order_number", order_id = db_order['buy_order_number'], reason="market_shifted_up")
                                        continue
                                    
                                    # 3.3
                                    elif market_window < 0:
                                        # the order may have been completed on exchange
                                        # verify if it has, and relate the order because of the fallen market window
                                        api_order = self.client.get_order_status_from_exchange(db_order)
                                        
                                        if api_order['status'] != "d":
                                            self.client.cancel_order(order_id_type = "buy_order_number", order_id = db_order['buy_order_number'], reason="market_shifted_down")
                                            continue
                                        
                                        else:
                                            self.client.prepare_leveled_buy_order("buy_order_number", db_order['buy_order_number'])
                                            
                                
                                elif api_order['status'] == "d":
                                    
                                    # 3.5
                                    if market_window < 0:
                                        # [6]
                                        self.client.prepare_leveled_buy_order(order_id = api_order['id'])
                                        continue
                                    
                                    # 3.4 and 3.6
                                    else:
                                        # [5 and 7]
                                        self.client.place_sell_order(db_order)
                                        continue
                                    
                                elif api_order['status'] == 'c':
                                    # order has been cancelled in exchange
                                    
                                    self.client.cancel_order(order_id_type = "buy_order_number", order_id = db_order['buy_order_number'], reason = "order_cancelled_in_exchange")
                                    continue
                               
                            elif db_order['type'] == "sell":
                                
                                if (api_order['status'] == "cd" or api_order['status'] == "a") and not self.client.has_order_expired(db_order):
                                    
                                    if market_window >= 0:
                                        continue
                                    
                                    
                                    elif market_window < 0:
                                        self.client.cancel_order("sell_order_number", api_order['id'], "market_shifted_down", db_order)
                                        
                                        
                                elif (api_order['status'] == "cd" or api_order['status'] == "a") and self.client.has_order_expired(db_order): 
                                    self.client.abandon_order(order_id_type = 'sell_order_number', order_id = api_order['id'])
                                    continue
                                
                                
                                elif (api_order['status'] == "c"):
                                    self.client.cancel_order(order_id_type = "sell_order_number", order_id = api_order['id'], reason = "order_cancelled_in_exchange")
                                    continue
                                
                                    
                                elif (api_order['status'] == "d"):
                                    self.client.close_order('sell_order_number', db_order['sell_order_number'])
                                
                                    
                                else:
                                    continue
                        else:
                            if api_order:
                                if "id" in api_order:
                                    self.client.cancel_order(order_id_type = "sell_order_number", order_id = api_order['id'], reason = "order_cancelled_in_exchange")
                                elif "error" in api_order:
                                    self.client.report("Difficulty getting order status. Client will try again. API response was: " + str(api_order))
                            else:
                                self.client.cancel_order(order_id_type = "sell_order_number", order_id = db_order['buy_order_number'], reason = "order_cancelled_in_exchange", db_order = db_order)
                                
                            continue
                        
                            
                except Exception, e:
                    #exc_type, exc_obj, exc_tb = sys.exc_info()
                    #fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    #print(exc_type, fname, exc_tb.tb_lineno)
                    
                    #self.client.off()
                    #self.client.report(str(e))
                    #self.client.report("An exception occurred. Stopping the client.")
                    
                    
                    exc_type, exc_obj, tb = sys.exc_info()
                    f = tb.tb_frame
                    lineno = tb.tb_lineno
                    filename = f.f_code.co_filename
                    linecache.checkcache(filename)
                    line = linecache.getline(filename, lineno, f.f_globals)
                    print 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)
                    
                    self.client.report("Client could not be initiated")
                    self.client.off()
            

                            
        else:
            self.client.report("Client could not be initiated")
            self.client.off()
            

    def stop_trade(self):
        """
        stop the trade
        """
        

        if self.client:
            if(self.state == 1):
                self.state = 2
                self.state_message = "Trade stopped"
                self.client.close_market()
                self.client.off()
                
                self.logger.info("ex.py::stop_trade: Stopping the client")
            else:
                self.state = -2;
                self.state_message = "Trade is not running and was not stopped"
                self.logger.info("ex.py::stop_trade: is not initialized and could not be stopped")
        