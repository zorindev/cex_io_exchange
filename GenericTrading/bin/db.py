'''
Created on Nov 2, 2017

@author: zorindev
'''

from config import db_name, db_host
import MySQLdb

import logging
from flask_socketio import emit

class DB(object):
    
    con = None
    
    def __init__(self, username, password, container):
        """
        establish connection
        """
        
        self.container = container
        self.ws = container.ws
        
        self.db = None
        
        try:
            self.db = MySQLdb.connect(
                    host = db_host,
                    user = username,
                    passwd = password,
                    db = db_name
                )  
            
        except Exception as e:
            self.container.state = -1
        
    
    def describe(self, cur):
        """
        combines descriptions and values
        """
        data = cur.fetchall()
        cols = [description[0] for description in cur.description]
        rtn = []
        for row in data:
            i = 0
            __row = {}
            for value in row:
                __row[cols[i]] = value
                i += 1
            rtn.append(__row)
        
        return rtn
    
    def query(self, sql, describe = False):
        """
        runs query
        """
        
        sql = sql.replace("\n", " ").strip()
        
        print sql
        
        try:
            cur = self.db.cursor()
            cur.execute(sql)
            
            if sql.startswith("select"):
                if describe:
                    return self.describe(cur)
                else:
                    return cur.fetchall()
            else:
                self.db.commit()
                return []
            
        except (MySQLdb.Error, MySQLdb.Warning) as e:
            self.container.client.report("Error running query: " + sql)
            self.container.client.report("Error: " + str(e))
            raise Exception("stopping client")
