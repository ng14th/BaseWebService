import os
import shutil
from pathlib import Path

import uvicorn

from app.gunicorn_runner import GunicornApplication
from app.settings import settings


def set_multiproc_dir() -> None:
    prom_dir = settings.prometheus_dir.expanduser().absolute()
    if prom_dir == Path.cwd().absolute() or prom_dir == Path("/"):
        raise ValueError(f"Dangerous prometheus_dir detected: {prom_dir}")

    shutil.rmtree(prom_dir, ignore_errors=True)
    prom_dir.mkdir(parents=True, exist_ok=True)

    os.environ["prometheus_multiproc_dir"] = str(prom_dir)
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = str(prom_dir)


def main() -> None:
    set_multiproc_dir()
    if settings.reload:
        uvicorn.run(
            "app.api.application:get_app",
            workers=settings.workers_count,
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
            log_level=settings.log_level.value.lower(),
            access_log=False,
            factory=True,
        )
        return

    GunicornApplication(
        "app.api.application:get_app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers_count,
        factory=True,
    ).run()


if __name__ == "__main__":
    main()
