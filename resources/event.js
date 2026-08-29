function EventReceiver(websocket, poller, channels, last_msg, onmessage) {
    var receiver = this;

    // Resolve dynamic WebSocket URL ensuring SSL & host match
    function resolveWsUrl(rawUrl) {
        var proto = (window.location.protocol === 'https:') ? 'wss://' : 'ws://';
        var host = window.location.host;
        if (!rawUrl) return proto + host + '/event/';
        if (rawUrl.indexOf('://') !== -1) {
            var clean = rawUrl.replace(/^wss?:\/\//, '');
            if (window.location.protocol === 'https:') {
                return 'wss://' + clean;
            }
            return rawUrl;
        }
        if (rawUrl.charAt(0) === '/') {
            return proto + host + rawUrl;
        }
        return proto + host + '/' + rawUrl;
    }

    this.websocket_path = resolveWsUrl(websocket);
    this.channels = channels;
    this.last_msg = last_msg || 0;
    this.poller_base = poller;
    this.poller_path = (poller || '/channels/') + channels.join('|');
    if (onmessage)
        this.onmessage = onmessage;

    this.websocket = null;
    this.onwsclose = null;
    this.is_polling = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 30;

    function init_poll() {
        if (receiver.is_polling) return;
        receiver.is_polling = true;

        function long_poll() {
            if (!receiver.is_polling) return;
            $.ajax({
                url: receiver.poller_path,
                data: {last: receiver.last_msg},
                success: function (data, status, jqXHR) {
                    if (data && data.message) {
                        receiver.onmessage(data.message);
                        if (data.id) {
                            receiver.last_msg = data.id;
                        }
                    }
                    if (receiver.is_polling) {
                        long_poll();
                    }
                },
                error: function (jqXHR, status, error) {
                    if (jqXHR.status === 504) {
                        if (receiver.is_polling) long_poll();
                    } else {
                        setTimeout(function() {
                            if (receiver.is_polling) long_poll();
                        }, 3000);
                    }
                },
                dataType: "json"
            });
        }
        long_poll();
    }

    function connectWs() {
        if (!window.WebSocket) {
            init_poll();
            return;
        }

        try {
            var ws = new WebSocket(receiver.websocket_path);
            var connectionTimeout = setTimeout(function () {
                if (ws && ws.readyState !== WebSocket.OPEN) {
                    try { ws.close(); } catch(e) {}
                    if (receiver.reconnectAttempts >= 3) {
                        init_poll();
                    }
                }
            }, 3500);

            ws.onopen = function (e) {
                clearTimeout(connectionTimeout);
                receiver.websocket = ws;
                receiver.is_polling = false;
                receiver.reconnectAttempts = 0;

                ws.send(JSON.stringify({
                    command: 'start-msg',
                    start: receiver.last_msg
                }));
                ws.send(JSON.stringify({
                    command: 'set-filter',
                    filter: receiver.channels
                }));
            };

            ws.onmessage = function (e) {
                try {
                    var data = JSON.parse(e.data);
                    if (data && data.message) {
                        receiver.onmessage(data.message);
                        if (data.id) {
                            receiver.last_msg = data.id;
                        }
                    }
                } catch(err) {
                    console.error('WebSocket message parse error:', err);
                }
            };

            ws.onclose = function (e) {
                clearTimeout(connectionTimeout);
                receiver.websocket = null;
                if (receiver.onwsclose) {
                    receiver.onwsclose(e);
                }

                // Auto-reconnect with backoff
                if (e.code !== 1000) {
                    receiver.reconnectAttempts++;
                    if (receiver.reconnectAttempts <= receiver.maxReconnectAttempts) {
                        var delay = Math.min(1000 * Math.pow(1.4, receiver.reconnectAttempts), 8000);
                        setTimeout(connectWs, delay);
                    } else {
                        init_poll();
                    }
                }
            };

            ws.onerror = function (e) {
                clearTimeout(connectionTimeout);
                try { ws.close(); } catch(err) {}
            };
        } catch(ex) {
            init_poll();
        }
    }

    connectWs();
}
