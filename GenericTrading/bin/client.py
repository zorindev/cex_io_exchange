'''
Created on Nov 18, 2017

@author: zorindev
'''

import sys
import os
import eventlet
if "pydev" not in sys.argv:
    eventlet.monkey_patch()

import sys
import time

from api import *
from config import *
from db import DB
from util import *

import logging
from random import randint
from random import uniform
import datetime

from flask_socketio import SocketIO, emit

class Client(object):
    """
    trading client, interfaces with API
    """
    
    msg_queue = {}
    msg_threshold = 5
    
    def __init__(
        self,
        exchange,
        market,
        ex_username, 
        ex_api_key,
        ex_api_secret,
        number_of_levels,
        level_percentage,
        lower_margin,
        upper_margin,
        profit_margin,
        min_asset_amount,
        container,
        ws
    ):
        """
        init client
        """
        
        self.init = True
        self.ws = ws
        self.container = container
        self.exchange = exchange
        self.market = market
        self.number_of_levels = int(number_of_levels)
        self.level_percentage = float(level_percentage)
        self.lower_margin = float(lower_margin)
        self.upper_margin = float(upper_margin)
        self.profit_margin = float(profit_margin)
        self.min_asset_amount = float(min_asset_amount)
        
        self.db = DB(decode(secret, db_username), decode(secret, db_password), container)
        self.api = API(exchange, ex_username, ex_api_key, ex_api_secret, self)
        
        self.price_precision = price_precision
        
        if self.init:
            self.balance_split = int(self.get_balance_split()) + 1
            
        else:
            self.report("Exchange configuration could not be loaded")
        
        self.__on  = False
        self.__off = False
        
        

    def reset(self):
        """
        on off reset
        """
        self.__on = self.__off = False
        
        
    def on(self):
        """
        order exec loop on
        """
        self.__on = not(self.__on or self.__off) or self.__on
        return self.__on
        
        
    def off(self):
        """
        order exec loop on
        """
        self.__off = True
        self.__on = False
        return self.__off
    
        
    def report(self, msg = ""):
        """
        report
        """
        if "PYDEV_COMPLETER_PYTHONPATH" not in os.environ.keys():
            
            now = datetime.datetime.now()
            str_tmstmp = now.strftime("%Y-%m-%d %H:%M")
            
            if msg in self.msg_queue:
                if ((self.msg_queue[msg] % self.msg_threshold) == 0):
                    self.ws.emit("ex_notification", {"id": self.container.id, "msg": str_tmstmp + ": " + msg}, namespace="/ex") 
                    self.container.logger.info(msg)
                       
                self.msg_queue[msg] += 1
                
            else:
                self.msg_queue[msg] = 1
                self.ws.emit("ex_notification", {"id": self.container.id, "msg": str_tmstmp + ": " + msg}, namespace="/ex")
                self.container.logger.info(msg)
            
        
        print(msg)
        
        self.api.wait()
        
        
    def get_balance_split(self):
        """
        get the count of markets in this exchange
        """
        
        return int(self.db.query(
            sql_get_balance_split_coeficent % 
                (self.exchange, ("%" + self.market.split("/")[1])), 
                describe = True
        )[0]['count'])
    
    
    def close_market(self):
        """
        updating market status
        """
        self.db.query((sql_exchange_markets_update % ("0", self.exchange, self.market)), describe = False)
        
    
    def is_order_count_exceeded(self):
        """
        checks if non completed order cound is lesss or equal than what the exchange allows
        """
        
        rtn = True
        db_incomplete_order_count = self.db.query((sql_get_in_progress_order_count % (self.exchange, self.market)), describe = True)
        try:
            if int(db_incomplete_order_count[0]['count']) <= int(self.api.number_of_open_orders):
                rtn = False
        except Exception, e:
            print e, str(e)
            self.report("Could not evaluate the number of open orders")
            self.off()
            
        return rtn
    
    
    def open_market(self):
        """
        sets market status to in use
        """
        self.db.query((sql_exchange_markets_update % ("1", self.exchange, self.market)), describe = False)
            
        
    def get_order_details_from_db(self):
        """
        gets order details from DB
        """
        db_orders = self.db.query((sql_get_open_orders_from_db % (self.exchange, self.market)), describe = True)
        return db_orders
    
    
    def set_price_precision(self, db_exchange_market):
        """
        sets price precision
        """
        if db_exchange_market:
            if "price_precision" in db_exchange_market:
                if int(db_exchange_market['price_precision']) > 0:
                    self.price_precision = int(db_exchange_market['price_precision'])
    
    
    def is_market_useable(self):
        """
        validates market
        """
        rtn = True
        db_exchange_market = (self.db.query((sql_exchange_markets % (self.exchange, self.market)), describe = True))[0]
        self.set_price_precision(db_exchange_market)
        
        if "order_age" in db_exchange_market and int(db_exchange_market['order_age']) > 0:
            self.api.sell_order_age = int(db_exchange_market['order_age'])
        
        if len(db_exchange_market) == 0:
            self.report("Market does not exist: " + self.exchange + "::" + self.market)
            rtn = False
            
        elif "in_use" in db_exchange_market:
            if db_exchange_market['in_use'] == 1:
                self.report("Market is already in use: " + self.exchange + "::" + self.market)
                rtn = False
                
        else:
            self.report("Market configuration error had occurred")
            rtn = False
                
        return rtn
    
    def get_trade_history(self):
        """
        gets trade history
        """
        
        return self.api.api_call(method = 'method_trade_history', pair = self.market, private = False, param = {})
    
    
    def trim_history(self, trade_history):
        """
        trims history
        """
        trimmed_history = [entry for entry in trade_history if int(entry['date'] * 1) > (int(time.time()) - self.api.order_history_age)]    
        return trimmed_history
    
    
    def calcuate_market_direction(self, trade_history = []):
        """
        calculate marker direction based on history
        """
        buys = list((buy for buy in trade_history if buy['type'] == 'buy'))
        
        buy_index = 0.00
        up = -1
        down = -1
        for buy in buys:
            if up == -1 and down == -1:
                buy_index = float((buy['price']) * 1)
                up = down = 0
                continue
     
            if float((buy['price']) * 1) > buy_index:
                down += 1
            elif float((buy['price']) * 1) < buy_index:
                up += 1
        
            buy_index = float((buy['price']) * 1)
        
        rtn = "up"
        if up < down:
            rtn = "down"
        
        return rtn
    
    
    def get_min_max_price(self):
        """
        gets a min & max from the ticker
        """
        ticker = self.api.api_call(method = "method_ticker", pair = self.market, private = False, param = {})
        return float(ticker['low']), float(ticker['high'])
    
    
    def calculate_average_bid_price(self, direction, adjust = False):
        """
        get average bid price from given history
        """
        
        bid = None
        sfx = 1
        order_book = self.api.api_call(method = "method_order_book", pair = self.market + "/?depth=" + str(self.api.order_book_depth), private = False, param = {})
        if(direction == "down"):
            bid = float(order_book['bids'][0][0])
        else:
            bid = float(order_book['asks'][0][0])
            sfx = -1
            
        if adjust:
            bid += (round(uniform((bid/1000), (bid/100)), 8) * sfx)
        
        return bid
    
    
    def calculate_bid_margin_percentage(self, avg_bid, low, high ):
        """
        calculates relationship between min, avg_bin and max
        """
        rtn = None
        
        print avg_bid, low, high
        
        if low < avg_bid and low < high and avg_bid < high and low > 0 and high > 0 and avg_bid > 0:
            high -= low
            avg_bid -= low
            one = high / 100
            avg_bid /= one
            rtn = int(avg_bid)
        else:
            rtn = 0
        
        return rtn
    
    def get_bid_amount(self):
        """
        gets the bid amount
        """
        
        min_asset_amount = 0
        currency_limits = (self.api.api_call(method = "method_currency_limits", pair = "", private = False, param = {}))['data']['pairs']
        symbol1, symbol2 = self.market.split("/")
        for pair in currency_limits:
            if pair['symbol1'] == symbol1 and pair['symbol2'] == symbol2:
                min_asset_amount = float(pair['minLotSize'])
                
        if self.min_asset_amount < min_asset_amount:
            self.min_asset_amount = min_asset_amount
        
        return float(self.min_asset_amount) + (float(self.min_asset_amount) / 10) + (randint(0,9) * (float(self.min_asset_amount) / 100)) + (randint(0,9) * (float(self.min_asset_amount) / 1000))
    
    
    def get_balance(self):
        """
        gets balance
        """
        
        balance_dict = self.api.api_call(method = "method_balance", pair = "", private = True, param = {})
        purchasing_currency = self.market.split("/")[1]
        
        balance = float(0.0)
        if(purchasing_currency in balance_dict):
            balance = float(balance_dict[purchasing_currency]['available'])
        
        if balance > 0 and self.balance_split > 0:
            balance /= self.balance_split
            
        return balance
    
    
    def sell_leveled_assets(self):
        """
        forces sale of leveled assets
        """
        
        
        if self.number_of_levels > 1:
            
            relationship = self.db.query(sql_does_relationship_exist % (self.market, self.exchange), describe = True)
            if len(relationship) == 1:
                
                related_order = self.db.query(sql_find_relationship % (self.market, self.exchange), describe = True)
                if len(related_order) == 1:
                    
                    related_orders = self.db.query(
                        sql_get_all_related_orders % (
                            related_order[0]['related_order_id'], 
                            self.market, 
                            self.exchange, 
                            related_order[0]['related_order_id'], 
                            self.market, 
                            self.exchange
                        ), describe = True)
                    
                    self.report("Relationships that were found are: " + str(related_orders))
                    
                    sell_price, asset_amount = self.calculate_leveled_profit_margin(related_orders, None)
                    self.report("Selling leveled assets. Sell price = " + str(sell_price) + "; asset amount = " + str(asset_amount))

                    params = self.api.get_method_params(
                        "submit_new_order", 
                        **({"order_type": "sell", "bid_price": round(sell_price, self.price_precision), "amount": round(asset_amount, 4)}))
                    api_order = self.api.api_call(method = "method_place_order", pair = self.market, private = True, param = params)
    
                    if "id" in api_order:
                        self.report(
                            "Placed final leveled sell order #" +\
                            str(api_order['id']) +\
                            " for " + str(asset_amount) +\
                            " " + self.market.split("/")[1] +\
                            " at " + str(sell_price) +\
                            " " + self.market.split("/")[0] +\
                            " on " + self.exchange + "."
                        )
                        
                    elif "error" in api_order:
                        self.report("Unable to submit final leveled sell order. Error: " + api_order['error'])
                        
            else:
                
                self.report("Could not sell leveled assets because number of relationships is not equal to 1. Relationship: " + str(relationship))
                        
        else:
            
            self.report("Could not sell lever assets because number of levels is not greater than 1: " + str(self.number_of_levels))
                        
        
        
    def submit_new_buy_order(self):
        """
        submit new buy order
        """
        
        trade_history = self.trim_history(self.get_trade_history())
        direction = self.calcuate_market_direction(trade_history)
        min_price, max_price = self.get_min_max_price()
        average_bid_price = self.calculate_average_bid_price(direction, adjust = True)
        margin_score = self.calculate_bid_margin_percentage(average_bid_price, min_price, max_price)
    
        if self.number_of_levels > 1:
            # stop the market if it had reached the 4th level
            relationship = self.db.query(sql_does_relationship_exist % (self.market, self.exchange), describe = True)
            if len(relationship) > 1:
                self.report("Order relationship issue was detected in " + self.exchange + " " + self.market + " and the trading is stopped.")
                self.close_market()
                self.off()
                return
              
            elif len(relationship) == 1:
                
                if self.check_order_market_level("''"):
                    self.report("Maximum trade levels have been reached. No new order can be submitted until existing orders are cleared.")
                    
                    self.sell_leveled_assets()
                    
                    self.db.query(sql_delete_started_order_relationship % (self.market, self.exchange))
                    self.close_market()
                    self.off()
                    return         
        
        self.report(
            "Attempting to place order: " +\
            "market = " + str(self.market) +\
            "; exchange = " + str(self.exchange) +\
            "; direction = " + str(direction) +\
            "; margin score = " + str(margin_score) +\
            "; min price = " + str(min_price) +\
            "; max_price = " + str(max_price) +\
            "; average_bid_price = " + str(average_bid_price)
        )
        
        if (direction == "up" and margin_score <= self.upper_margin) or (direction == "down" and margin_score >= self.lower_margin and margin_score <= self.upper_margin): 
            """
            place order
            """ 
            
            self.report("Submitting new buy order")
            
            amount = self.get_bid_amount()
            balance = self.get_balance()
        
            if(((average_bid_price * amount) * self.api.fee) <= balance):
                
                # submit order
                params = self.api.get_method_params("submit_new_order", **({"order_type": "buy", "bid_price": round(average_bid_price, self.price_precision), "amount": round(amount, 4)}))
                api_order = self.api.api_call(method = "method_place_order", pair = self.market, private = True, param = params)
                
                if "id" in api_order:
                    # track order and report
                    self.db.query(
                        (sql_track_new_buy_order % (api_order['id'], self.exchange, self.market,  str(average_bid_price), str(amount), 'buy', 'o', api_order['time'])))
                    
                    self.report(
                        "submitted new buy order " + api_order['id'] + 
                        "to " + self.exchange + 
                        " to purchase " + str(amount) +
                         " of " + self.market.split("/")[0] + 
                         " for " + str(average_bid_price) + 
                         " of " + self.market.split("/")[1]
                    )
                    
                    if self.number_of_levels > 1:
                        # manage order relationship
                        if relationship and len(relationship) == 1:
                            self.db.query(sql_update_order_relationship % (api_order['id'], relationship[0]['order_id'], self.market, self.exchange))
                else:
                    self.report("Error placing the buy order: " + api_order['error'])
                    
            else:
                self.report(
                    "Insufficient funds on " + 
                    self.exchange + 
                    " to purchase " + 
                    str(amount) + 
                    " of " + self.market.split("/")[0] + 
                    " for " + str(average_bid_price) + 
                    " of " + self.market.split("/")[0]
                )
                
                
                if self.number_of_levels > 1:
                    
                    self.sell_leveled_assets()
                    
                    self.db.query(sql_delete_started_order_relationship % (self.market, self.exchange))
                    
                    self.close_market()
                    self.off()
                    return                                         
                    
    
        
                                
    
    def get_order_status_from_exchange(self, db_order = None):
        """
        get order status from exchange
        """
        
        order_id = db_order['buy_order_number']
        if db_order['type'] == 'sell':
            order_id = db_order['sell_order_number']
            
        params = self.api.get_method_params("get_order_status_from_exchange", **({"id": order_id}))
        api_order = self.api.api_call(method = "method_get_order", pair = '', private = True, param = params)
        return api_order
        
            
    def get_market_window(self, db_order = None):
        """
        compares buy or sell price of the order to the current average bid price
        """
        
        market_window = 0
        change = 0
        
        try: 
            if db_order:
                price = 0.0
                if db_order['sell_price']:
                    price = float(db_order['sell_price'])
                else:
                    price = float(db_order['buy_price'])
                    
                trade_history = self.trim_history(self.get_trade_history())
                direction = self.calcuate_market_direction(trade_history)
                average_bid_price = float(self.calculate_average_bid_price(direction))
                
                if price > average_bid_price:
                    market_window = -1
                    change = ((price - average_bid_price) / price)
                    
                elif price < average_bid_price:
                    market_window = 1
                    change = ((average_bid_price - price) / average_bid_price)
            
            if change <= self.level_percentage or (self.number_of_levels == 1 and market_window == -1):
                # if change is insignificant then do not report market change
                market_window = 0
                     

        except Exception, e:
            self.off()
            self.report("Error encountered while gethering market_window details. " + self.exchange + " " + self.market)
            
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            raise Exception(str(e) + " " + exc_type + " " + fname + " " + exc_tb.tb_lineno)
                
        return market_window
    
    
    def check_order_market_level(self, order_id = None):
        """
        cheks the number of related orders
        """
        
        if order_id or len(order_id) == 0:
            
            count = (self.db.query(sql_get_number_of_related_records % (order_id, self.market, self.exchange, order_id, self.market, self.exchange), describe = True))[0]['count']
            
            rtn = False
            try:
                if int(count) >= self.number_of_levels:
                    rtn = True
            except:
                pass
            
            return rtn
            
    
    def cancel_order(self, order_id_type = "buy_order_number", order_id = None, reason = None, db_order = None):
        """
        cancel order
        """
        
        if order_id and reason:
             
            params = self.api.get_method_params("cancel_order", **({"order_id": order_id}))
            cancel_response = self.api.api_call(method = "method_cancel_order", pair = "", private = True, param = params)
            
            if cancel_response:
                
        
                if reason == "market_shifted_down":
                                        
                    if order_id_type == "buy_order_number":
                        # find parent order
                        parent_order = self.db.query(sql_get_parent_order % (order_id, self.market, self.exchange), describe = True)
                        
                        # if parent order then remove this relationship
                        if len(parent_order) == 1:
                            self.db.query(sql_update_order_relationship_undo % ("''", parent_order[0]['parent_order'], order_id, self.market, self.exchange), describe = True)
                            
                        self.report("Buy order " + order_id + " on " + self.exchange + " " + self.market + " is above the market position. Canceling order.")
                        self.db.query(sql_set_order_status % ("n", order_id_type, order_id))
                            
                    
                    else:
                        
                        parent_order = self.db.query(sql_get_parent_order % (db_order['buy_order_number'], self.market, self.exchange), describe = True)
                    
                        if len(parent_order) == 1 or (len(parent_order) == 0 and self.number_of_levels > 1):
                            self.prepare_leveled_buy_order("buy_order_number", db_order['buy_order_number'])
                        
                        else:
                            
                            self.report("Sell order " + order_id + " on " + self.exchange + " " + self.market + " is below the market position. Canceling order.")
                            self.db.query(sql_set_order_status % ("n", order_id_type, order_id))
                            
                            
                elif reason == "order_cancelled_in_exchange":
                    self.report("Order " + order_id + " on " + self.exchange + " " + self.market + " has been cancelled in exchange.")
                    self.db.query(sql_set_order_status % ("n", order_id_type, order_id))
                    
                    
                elif reason == "market_shifted_up":
                    
                    if order_id_type == "buy_order_number":
                        
                        # find parent order
                        parent_order = self.db.query(sql_get_parent_order % (order_id, self.market, self.exchange), describe = True)
                        
                        # if parent order then remove this relationship
                        if len(parent_order) == 1:
                            self.db.query(sql_update_order_relationship_undo % ("''", parent_order[0]['parent_order'], order_id, self.market, self.exchange), describe = True)
                            
                        self.report("Buy order " + order_id + " on " + self.exchange + " " + self.market + " is below the market position. Canceling order.")
                        self.db.query(sql_set_order_status % ("n", order_id_type, order_id))
                                    
                    
            else:
                self.report("Unable to cancel order " + order_id + "; response was " + str(cancel_response))
                raise Exception("Unable to cancel order " + order_id + "; response was " + str(cancel_response))
                
                
                
    def get_parent_order(self, order_id_type = "buy_order_number", order_id = None):
        """
        get parent order
        """
        
        if "sell" in order_id_type:
            try:
                order_id = self.db.query(sql_get_buy_order_from_sell_order %(order_id), describe = True)[0]['buy_order_number']
            except:
                self.report("Could not lookup a buy order number for sell order number = " + order_id + ". Closing the market.")
                self.off()
                self.close_market()
        
        parent_order = self.db.query(sql_get_parent_order % (order_id, self.market, self.exchange), describe = True)
        return parent_order
        
                
    def prepare_leveled_buy_order(self, order_id_type = "buy_order_number", order_id = None):
        """
        set leveled buy order records
        """
        
        if self.number_of_levels > 1:
            self.db.query(sql_set_order_status % ("l", order_id_type, order_id))
            parent_order = self.get_parent_order(order_id_type, order_id)
            
            if len(parent_order) == 0:
                # this is the first order
                self.db.query(sql_create_order_relationship % (order_id, self.market, self.exchange))
                
            elif len(parent_order) == 1:
                # order relationship for this order already existed
                # it means that we have to create a new relationship for the future order    
                self.db.query(sql_create_order_relationship % (parent_order[0]['parent_order'], self.market, self.exchange))
            
            
    def calculate_leveled_profit_margin(self, related_orders, db_order = None):
        """
        calculates neccessary profit margin from related orders 
        """
        
        sell_price = float(0.0)
        avg_price = float(0.0)
        asset_amount = float(0.0)
        
        self.profit_margin = float(self.profit_margin) + 0.0025        
        if float(self.profit_margin) < 1:
            self.profit_margin = float(self.profit_margin) + 1.0
        
        if len(related_orders) > 0:
            for order in related_orders:
                avg_price += float(order['buy_price'])
                asset_amount += float(order['asset_buy_amount'])
                
            sell_price = (round(avg_price / len(related_orders), self.price_precision) * self.profit_margin)
                
        elif len(related_orders) == 0 and db_order:
            asset_amount = float(db_order['asset_buy_amount'])
            sell_price = float(db_order['buy_price']) * float(self.profit_margin)
            
        
        return sell_price, asset_amount
                        
                        
    def place_sell_order(self, db_order = None):
        """
        place sell order
        """
        
        
        buy_order_id = db_order['buy_order_number']
        
        # get related orders
        related_orders = self.db.query(sql_get_all_related_orders % (buy_order_id, self.market, self.exchange, buy_order_id, self.market, self.exchange), describe = True)
        sell_price, asset_amount = self.calculate_leveled_profit_margin(related_orders, db_order)
        
        
        if float(sell_price) > (db_order['buy_price']):
            params = self.api.get_method_params("submit_new_order", **({"order_type": "sell", "bid_price": round(sell_price, self.price_precision), "amount": round(asset_amount, 4)}))
            api_order = self.api.api_call(method = "method_place_order", pair = self.market, private = True, param = params)
            
            if "id" in api_order:
                self.db.query(sql_track_sell_order % (api_order['id'], sell_price, asset_amount, 'o', buy_order_id))
                self.report(
                    "Placed sell order #" +\
                    str(api_order['id']) +\
                    " for " + str(asset_amount) +\
                    " " + self.market.split("/")[1] +\
                    " at " + str(sell_price) +\
                    " " + self.market.split("/")[0] +\
                    " on " + self.exchange + "."
                )
                
            elif "error" in api_order:
                self.report("Unable to submit sell order. Error: " + api_order['error'])
                self.cancel_order(
                    order_id_type = "buy_order_number", 
                    order_id = db_order['buy_order_number'], 
                    reason = "order_cancelled_in_exchange", 
                    db_order = db_order
                )
                
        else:
            self.report("Not a profitable margin: buy price = " + str(db_order['buy_price']) + "; sell price = " + str(sell_price))
        
    
    def has_order_expired(self, db_order = None):
        """
        check if order had expired
        """
        rtn = False
        if db_order:
            self.report("Checking if order " + str(db_order['sell_order_number']) + " has expired: time = " + str(time.time()) + "; db_time = " + str(int(db_order['last_updated_timestamp'])) + "; age = " + str(self.api.sell_order_age))
            if (int(time.time()) - int(db_order['last_updated_timestamp'])) > self.api.sell_order_age:
                rtn = True
                
        return rtn
        
    
    def abandon_order(self, order_id_type = 'buy_order_number', order_id = None):
        """
        abandon order
        """
        if order_id:
            self.report("Abandoning order " + str(order_id))
            self.db.query(sql_set_order_status % ("a", 'sell_order_number', order_id))
        
        
    def close_order(self, order_id_type = 'buy_order_number', order_id = None):
        """
        close order
        """
        if order_id:
            self.db.query(sql_set_order_status % ("d", 'sell_order_number', order_id))
        
    
    