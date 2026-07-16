from pydantic import AnyHttpUrl, Field


class Security:
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    backend_cors_origins: list[AnyHttpUrl] = Field(default_factory=list)
    users_secret: str = ""
    private_key_encrypt_pw: str = ""
    app_secret: str = ""

    trusted_proxy_ips: list[str] = Field(default_factory=list)
    docs_enabled: bool = True
    metrics_enabled: bool = True
