$(document).ready(function(){
	
    
    namespace = '/ex';
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + namespace);
	
	socket.on('connected', function(msg) {
	    $("div.ex_console").append("connected");
	});
});

