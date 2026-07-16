import sys

from loguru import logger

from app.settings import settings


def configure_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level.value)
