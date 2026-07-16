class GunicornSetting:
    workers_count: int = 2
    limit_concurrency: int = 1000
    timeout_keep_alive: int = 20

    timeout: int = 70
    graceful_timeout: int = 20

    max_requests: int = 3000
    max_requests_jitter: int = 30

    preload_app: bool = True
    reuse_port: bool = True
