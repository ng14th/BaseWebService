from datetime import timezone as dt_timezone

# from celery.schedules import crontab
from kombu import Exchange, Queue

from app.settings import settings

redis_url = str(settings.redis_url)

CELERY_BROKER_URL = redis_url
result_backend = redis_url
accept_content = ["application/json"]

timezone = dt_timezone.utc
result_extended = True


CELERY_POOL_RESTARTS = True
CELERY_TASK_IGNORE_RESULT = False
CELERY_TASK_SOFT_TIME_LIMIT = 10800  # seconds
CELERY_TASK_TIME_LIMIT = 10800  # seconds

CELERY_TASK_DEFAULT_EXCHANGE = settings.celery_default_queue
CELERY_TASK_DEFAULT_QUEUE = settings.celery_default_queue
CELERY_TASK_DEFAULT_ROUTING_KEY = settings.celery_default_queue

CELERY_TASK_CREATE_MISSING_QUEUES = False

CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True


# TASK_DAILY_METRICS_ROLLUP = {
#     "xx": {
#         "task": "xx",
#         "schedule": crontab(minute="0", hour="18"),  # 01:00 AM VN
#         "options": {"queue": CELERY_TASK_DEFAULT_QUEUE},
#         "args": {},
#     },
# }


CELERY_BEAT_SCHEDULE = {
    # **TASK_DAILY_METRICS_ROLLUP,
}

CELERY_TASK_QUEUES = (
    Queue(
        CELERY_TASK_DEFAULT_QUEUE,
        Exchange(
            CELERY_TASK_DEFAULT_EXCHANGE,
            # The delivery_mode changes how the messages to this queue are delivered.
            # A value of one means that the message won’t be written to disk,
            # and a value of two (default) means that the message can be written to disk.
            delivery_mode=2,
        ),
        routing_key=CELERY_TASK_DEFAULT_ROUTING_KEY,
        # Durable exchanges are persistent (i.e., they survive a broker restart).
        durable=True,
    ),
    Queue(),
)
