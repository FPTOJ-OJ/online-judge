module.exports = {
    get_host: '127.0.0.1',        // Server xử lý GET requests
    get_port: 15100,              // Cổng cho sự kiện GET (phải khớp với nginx)
    post_host: '127.0.0.1',       // Server xử lý POST requests
    post_port: 15101,             // Cổng cho sự kiện POST (phải khớp với local_settings.py)
    http_host: '127.0.0.1',       // Server HTTP requests
    http_port: 15102,             // Cổng HTTP (phải khớp với nginx)
    long_poll_timeout: 29000,     // Timeout cho long polling (milisecond)
};
