class HttpClientSetting:
    http_max_connections: int = 200
    http_max_keepalive_connections: int = 50
    http_pool_timeout_seconds: float = 5.0
    http_max_concurrent_requests: int = 100
