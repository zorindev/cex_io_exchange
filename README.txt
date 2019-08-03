README

This application is an attempt to automate trading on CEX.IO as well as other exchanges. 
It was initially designed to handle CEX.IO API and the trading logic was connected to other
exchange API's through exchange specific adapter (e.g. bitfinex, bittrex (work in progress)).

The application is built with Flask web framework. It is designed to launch multiple trading sessions on a single screen.
Communication between UI and back end is performed through web sockets. Eventlet is employed to handle websocket architecture on the back end.

Various data is persisted in sqlite3 local static database.

The trading algorithm is trivial and impractical but could enhanced. It relies on compensating purchases in the event of price fall.
At the moment entry position calculation is trivial. It can be enhanced with additional evaluators (stochastics, bollinger, moving average, etc).