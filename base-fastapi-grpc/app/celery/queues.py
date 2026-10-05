from kombu import Exchange, Queue

from app.settings import settings


def _make_queue(name: str) -> Queue:
    return Queue(
        name,
        Exchange(name, delivery_mode=2),
        routing_key=name,
        durable=True,
    )


task_queues = tuple(_make_queue(q) for q in (settings.celery_default_queue,))
