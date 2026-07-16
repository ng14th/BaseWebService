class CelerySetting:
    celery_app_name: str = "my-app-celery"
    celery_task_timeout: int = 1800
    celery_default_queue: str = "my-app-queue-tasks"
