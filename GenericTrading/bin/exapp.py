#!/usr/bin/env python
import eventlet
#eventlet.monkey_patch()

#import newrelic.agent
#newrelic.agent.initialize('newrelic.ini')

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


@app.route('/')
def main():
    return render_template('exview.html')


@socketio.on('connect', namespace='/ex')
def ws_conn():
    socketio.emit('connected', {'data': "connected"}, namespace='/ex')

	
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)#