from app.settings import settings

# Default options for tasks
DEFAULT_OPTIONS = {"queue": settings.celery_default_queue}


def make_task(task_name, schedule, options=None, args=None, kwargs=None):
    """
    Create a Celery beat task configuration.

    Args:
        task_name: Full dotted path to the task
        schedule: Celery schedule object (e.g., crontab)
        options: Task execution options (default: DEFAULT_OPTIONS)
        args: Positional task arguments (default: empty tuple)
        kwargs: Keyword task arguments (default: empty dict)

    Returns:
        dict: Task configuration dictionary
    """
    return {
        "task": task_name,
        "schedule": schedule,
        "options": options or DEFAULT_OPTIONS,
        "args": () if args is None else args,
        "kwargs": {} if kwargs is None else kwargs,
    }


# Example:
# from celery.schedules import crontab
#
# TASK_DAILY_METRICS_ROLLUP = {
#     "task_daily_metrics_rollup": make_task(
#         task_name="app.tasks.daily_metrics_rollup_task",
#         schedule=crontab(minute="0", hour="18"),  # 01:00 AM VN
#     ),
# }
