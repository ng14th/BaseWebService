class CircuitBreakerSetting:
    circuit_breaker_enabled: bool = True
    circuit_breaker_timeout_threshold: int = 3
    circuit_breaker_timeout_window_seconds: int = 60
    circuit_breaker_open_seconds: int = 60
    circuit_breaker_half_open_success_threshold: int = 3
