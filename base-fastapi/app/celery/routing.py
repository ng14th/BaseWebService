from app.settings import settings

# default routing
task_routes = {
    "*": {"queue": settings.celery_default_queue},
}
