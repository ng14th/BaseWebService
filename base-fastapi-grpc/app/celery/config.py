from datetime import timezone as dt_timezone

from app.celery.beat import beat_schedule  # noqa
from app.celery.queues import task_queues  # noqa
from app.celery.routing import task_routes  # noqa
from app.settings import settings

redis_url = str(settings.redis_url)

# Redis
broker_url = redis_url
result_backend = redis_url


# Serialization
accept_content = ["json"]
task_serializer = "json"
result_serializer = "json"

# Timezone
timezone = dt_timezone.utc
enable_utc = True

# Result
result_extended = True
task_ignore_result = False

# Worker
worker_pool_restarts = True
worker_send_task_events = True

# Task
task_send_sent_event = True
task_soft_time_limit = 10800
task_time_limit = 10800

task_default_exchange = settings.celery_default_queue
task_default_exchange_type = "direct"
task_default_queue = settings.celery_default_queue
task_default_routing_key = settings.celery_default_queue
task_create_missing_queues = False
