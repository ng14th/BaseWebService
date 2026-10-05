# Merge periodic task groups defined in app.celery.schedule, e.g.:
# from app.celery.schedule import TASK_DAILY_METRICS_ROLLUP
#
# beat_schedule = {
#     **TASK_DAILY_METRICS_ROLLUP,
# }
beat_schedule: dict = {}
