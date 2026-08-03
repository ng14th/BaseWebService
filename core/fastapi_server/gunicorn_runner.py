from typing import Any

from gunicorn.app.base import BaseApplication
from gunicorn.util import import_app
from uvicorn.workers import UvicornWorker

from app.settings import settings


class CustomUvicornWorker(UvicornWorker):
    CONFIG_KWARGS: dict[str, Any] = {  # noqa: RUF012
        "loop": "uvloop",
        "http": "httptools",
        "limit_concurrency": settings.limit_concurrency,
        "timeout_keep_alive": settings.timeout_keep_alive,
        "factory": True,
    }


class GunicornApplication(BaseApplication):
    def __init__(
        self,
        app: str,
        host: str,
        port: int,
        workers: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.options = {
            "bind": f"{host}:{port}",
            "workers": workers or settings.workers_count,
            "worker_class": "core.fastapi_server.gunicorn_runner.CustomUvicornWorker",
            "timeout": settings.timeout,
            "graceful_timeout": settings.graceful_timeout,
            "max_requests": settings.max_requests,
            "max_requests_jitter": settings.max_requests_jitter,
            "reuse_port": settings.reuse_port,
            "loglevel": settings.log_level.value.lower(),
            **kwargs,
        }
        self.app = app
        super().__init__()

    def load_config(self) -> None:
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:  # type: ignore
                self.cfg.set(key.lower(), value)  # type: ignore

    def load(self) -> str:
        return import_app(self.app)
