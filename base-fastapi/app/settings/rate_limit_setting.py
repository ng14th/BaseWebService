class RateLimitSetting:
    rate_limit_enabled: bool = False
    rate_limit_by_ip_enabled: bool = True
    rate_limit_ip_requests: int = 120
    rate_limit_ip_window_seconds: int = 60
    rate_limit_by_client_id_enabled: bool = True
    rate_limit_client_id_requests: int = 300
    rate_limit_client_id_window_seconds: int = 60
    rate_limit_client_id_header: str = "x-client-id"
    rate_limit_trust_proxy_headers: bool = False

    rate_limit_watch_retries: int = 5
