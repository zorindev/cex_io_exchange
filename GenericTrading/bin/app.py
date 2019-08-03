#!/usr/bin/env python

""" ENVIRONMENT """

import sys
import os
import eventlet
if "pydev" not in sys.argv:
    eventlet.monkey_patch()



from flask import Flask, render_template, request, g, session, make_response, current_app, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user , logout_user , current_user , login_required, UserMixin
from threading import Lock, Thread, Event


import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

global_logger = logging.getLogger("Logger")
global_logger.setLevel(logging.DEBUG)

rttng_hndlr = RotatingFileHandler("logs/log_new.txt", maxBytes = (1024 * 1000), backupCount = 5)
rttng_hndlr.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
console_handler = StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

global_logger.addHandler(rttng_hndlr)
global_logger.addHandler(console_handler)


""" Application """
from ex import Ex
from config import *

""" Init FLASK and Socket Server """
app = Flask(__name__)
app.config['SECRET_KEY'] = secret
socketio = SocketIO(app, async_mode='eventlet')
login_manager = LoginManager()
login_manager.init_app(app)
            
# EX threads
workers = {}

# users
users = {'foo': {'password': 'bar'}}


class User(UserMixin):
    """
    user authentication class
    """
    pass
    
    
@login_manager.user_loader
def user_loader(username):
    """
    user loader
    """
    
    if username not in users:
        return 
    
    user = User()
    user.id = username
    return user


@login_manager.request_loader
def request_loader(request):
    """
    request loader
    """
    username = request.form.get('username')
    if username not in users:
        return
    
    user = User()
    user.id = username
    user.is_authenticated = request.form['password'] == users[username]['password']
    
    return user


@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized'


###########
# Routing #
###########
@app.route("/login", methods = ['POST', 'GET'])
def login():
    """
    login
    """
    if request.method == 'GET':
        return render_template("login.html")
    
    username = request.form['username']
   
    if request.form['password'] == users[username]['password']:
        user = User()
        user.id = username
        login_user(user)
        return redirect(url_for("index"))
    

@app.route("/logout")
def logout():
    """
    logout
    """
    logout_user()
    return redirect(url_for('index'))


@login_manager.unauthorized_handler
def unauthorized_callback():
    """
    un auth redirect
    """
    return redirect('/login')


@app.route('/')
@login_required
def index():
    """
    renders the home page
    """    
    return render_template('index.html', page_title = "Trading Client")


@app.before_request
def before_request():
    """
    before request
    """
    g.user = current_user
    

########################
# SOCKETIO connections #
########################

@socketio.on('connect', namespace='/ex')
def connect():
    """
    clients connect
    """
    
    global_logger.info("Client connected")
    emit("re_connect")
    

@socketio.on('trigger', namespace='/ex')
def trigger(data): 
    """
    triggers the trade
    """
    
    global workers
    
    print data
    
    if data['id'] not in workers:
        workers[data['id']] = Ex(data['id'], socketio, global_logger)
        workers[data['id']].set_trade_parameters(data)
        socketio.start_background_task(target=workers[data['id']].run_trade)
        emit("re_trigger", {'id': data['id'], 'state': '', 'state_message': 'worker with id ' + data['id'] + ' connected'})
    else:
        global_logger.info("app.py::trigger: Client was not started")
        emit("re_trigger", {'id': data['id'], 'state': '', 'state_message': 'worker with id ' + data['id'] + ' already exists'})
    
        
@socketio.on('stop_trade', namespace='/ex')
def stop(data): 
    """
    stop the trade
    """
    
    
    if data['id'] in workers:
        workers[data['id']].stop_trade()
        emit("re_stop_trade", {'id': data['id'], 'state': workers[data['id']].state, 'state_message': workers[data['id']].state_message})
        
        _workers = dict(workers)
        del _workers[data['id']]
         
    else:
        global_logger.info("app.py::stop: id " + data['id'] + " was not in the list of workers.")
        emit("re_stop_trade", {'id': data['id'], 'state': '', 'state_message': 'worker with id ' + data['id'] + ' could not be found'})
        
    
@socketio.on('disconnect', namespace='/ex')
def disconnect():
    """
    disconnect client
    """
    emit('re_disconnect')


if __name__ == '__main__':
    """
    launch server
    """
    
    """
    TODO:
    
        fix shared nonce
        
        develop standard response payload
        
        change entry position to be based on bolinger, stockastic oscolator, and fibonaci ratios where possible
        
        introduce monitoring and trading modes
        
        add UI graph for bolinger, stochastic, candles, bot buy and bot sell events
        
        improve UI for properly submitting input data
        
    """
    
    
    if "PYDEV_COMPLETER_PYTHONPATH" in os.environ.keys():
        payload = {
            "id": "1", 
                "data": [
                    "jSNiRrzNOpTmEde6vFap",
                    "cex.io",
                    "BTG/USD",
                    "zorindev",
                    "ftRd4H1bMepgx7WsjRYLlOznZM",
                    "915d8lx92ocbn9jtlTkz2zlkuuk",
                    "25",
                    "75",
                    "1.005", # profit margin
                    "0.01", # min trade amount
                    "4",    # number of levels
                    "0.01"   # level percentage
                ]
        }
        
        ex = Ex("1", socketio, global_logger)
        ex.set_trade_parameters(payload)
        ex.run_trade()
        
    else:
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)

        