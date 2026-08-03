# -*- coding: utf-8 -*-
import asyncio
import os
from typing import Any, Awaitable

from celery import Celery
from celery.signals import worker_init, worker_process_init, worker_process_shutdown

from app.settings import settings
from core.db.lifespan import dispose_engines
from core.infra.otelemetry import setup_opentelemetry
from core.infra.redis.lifespan import init_redis, shutdown_redis_client
from core.infra.system_log.mongo import MongoClientSingleton
from core.logging.log import configure_logging

app = Celery(settings.celery_app_name)

# Set env variable for celery worker using NullPool instead of default pool
os.environ.setdefault("CELERY_WORKER", "1")

app.config_from_object("app.celery.config", namespace="CELERY")

app.conf.task_default_queue = settings.celery_default_queue
app.conf.task_default_exchange_type = "direct"
app.conf.task_default_routing_key = settings.celery_default_queue
app.conf.task_queue_max_priority = 10
app.conf.task_default_priority = 5

app.conf.update(
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
)

# default routing
app.conf.task_routes = {
    "*": {"queue": settings.celery_default_queue},
}

app.autodiscover_tasks(["app.celery"], related_name="tasks")


# _WORKER_LOOP is a global variable at the OS Process level.
# In Celery's prefork pool, each Child Process has its own isolated memory space.
# Therefore, each worker process will have exactly ONE unique _WORKER_LOOP.
# All tasks executed by a specific worker process will run sequentially on its Main Thread
# and share this exact same event loop,
# allowing them to reuse connection pools (Redis, DB, Mongo).
_WORKER_LOOP: asyncio.AbstractEventLoop | None = None
_BOOTSTRAPPED_PIDS: set[int] = set()


def init_db() -> None:
    from core.db.engine_routing import READ_ENGINE, WRITE_ENGINE  # noqa


def get_worker_loop() -> asyncio.AbstractEventLoop:
    """
    Retrieve or create the single Event Loop for the current Worker Process.
    """
    global _WORKER_LOOP

    if _WORKER_LOOP is None or _WORKER_LOOP.is_closed():
        _WORKER_LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_WORKER_LOOP)

    return _WORKER_LOOP


def _bootstrap_worker() -> None:
    """
    Initialize resources for the current OS Process.
    """
    pid = os.getpid()

    if pid in _BOOTSTRAPPED_PIDS:
        return

    configure_logging()
    setup_opentelemetry()

    # Init async-bound clients AFTER the event loop is created.
    # By creating the loop first,
    # connection pools (Redis, DB) will bind to this exact loop.
    get_worker_loop()

    init_db()
    init_redis()

    _BOOTSTRAPPED_PIDS.add(pid)


@worker_init.connect(weak=False)
def init_worker(sender=None, *args: Any, **kwargs: Any) -> None:
    """
    This signal is called ONCE in the Main (Master)
    Process BEFORE any Child Processes are forked.
    """
    pool_cls = str(getattr(sender, "pool_cls", "")).lower()

    # If using 'prefork',
    # the OS will fork() the Main Process to create Child Processes.
    # We MUST NOT initialize TCP connections (DB/Redis) here in the Main Process,
    # because if we do,
    # all Child Processes will inherit and share the EXACT SAME TCP socket,
    # leading to data corruption, network errors, and connection drops.
    if "prefork" in pool_cls:
        configure_logging()  # Safe to configure logging here
        return

    # For 'solo' or 'threads' pools (where no fork() happens),
    # we must initialize everything here.
    _bootstrap_worker()


@worker_process_init.connect(weak=False)
def init_worker_process(*args: Any, **kwargs: Any) -> None:
    """
    This signal is called in the Child Process AFTER it has been successfully forked.
    It is 100% safe to initialize network resources here because they will be native
    and exclusive to this specific Child Process memory space.
    """
    _bootstrap_worker()


@worker_process_shutdown.connect(weak=False)
def shutdown_worker_process(*args: Any, **kwargs: Any) -> None:
    """
    Called when a Child Process is about to die
    (e.g., reaching --max-tasks-per-child=1000).
    We cleanly shut down the Event Loop to free up OS resources before the process exits.
    """
    global _WORKER_LOOP

    if _WORKER_LOOP and not _WORKER_LOOP.is_closed():

        _WORKER_LOOP.run_until_complete(shutdown_redis_client())
        MongoClientSingleton.close()
        _WORKER_LOOP.run_until_complete(dispose_engines())
        _WORKER_LOOP.run_until_complete(_WORKER_LOOP.shutdown_asyncgens())
        _WORKER_LOOP.close()

    _WORKER_LOOP = None


def run_async(coro: Awaitable[Any]) -> Any:
    """
    Run async code inside Celery sync task context.

    Instead of using asyncio.run() (which creates and closes a new loop every time),
    we fetch the shared _WORKER_LOOP of the current Worker Process.
    This means Task 1, Task 2... Task 1000 will run sequentially on the exact same loop.
    As a result,
    they can safely reuse the already open TCP connections in the DB/Redis pools,
    avoiding the "Event loop is closed" error and dramatically boosting performance.
    """
    loop = get_worker_loop()

    if loop.is_running():
        raise RuntimeError("Celery worker event loop is already running")

    return loop.run_until_complete(coro)
