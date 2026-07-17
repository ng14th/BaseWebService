import logging
import sys
from typing import TYPE_CHECKING, Union

from loguru import logger

if TYPE_CHECKING:
    from loguru import Record

from opentelemetry.trace import INVALID_SPAN, INVALID_SPAN_CONTEXT, get_current_span

from app.settings import settings


def get_trace_id_span_id():
    span = get_current_span()
    if span and span.get_span_context().is_valid:
        ctx = span.get_span_context()
        return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    return "0", "0"


class InterceptHandler(logging.Handler):
    """
    Default handler from examples in loguru documentation.

    This handler intercepts all log requests and
    passes them to loguru.

    For more info see:
    https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        """
        Propagates logs to loguru.

        :param record: record to log.
        """
        try:
            level: Union[str, int] = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def record_formatter(record: "Record") -> str:  # pragma: no cover
    """
    Formats the record.

    This function formats message
    by adding extra trace information to the record.

    :param record: record information.
    :return: format string.
    """
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
        "| <level>{level: <8}</level> "
        "| <magenta>trace_id={extra[trace_id]}</magenta> "
        "| <blue>span_id={extra[span_id]}</blue> "
        "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
        "- <level>{message}</level>\n"
    )

    # Prefer values injected via middleware (contextvars / contextualize),
    # then fall back to opentelemetry span context, else 0.
    record["extra"].setdefault("span_id", 0)
    record["extra"].setdefault("trace_id", 0)

    span_id = record["extra"].get("span_id") or 0
    trace_id = record["extra"].get("trace_id") or 0

    if not span_id or not trace_id:
        span = get_current_span()
        if span != INVALID_SPAN:
            span_context = span.get_span_context()
            if span_context != INVALID_SPAN_CONTEXT:
                record["extra"]["span_id"] = span_id or format(
                    span_context.span_id, "016x"
                )
                record["extra"]["trace_id"] = trace_id or format(
                    span_context.trace_id, "032x"
                )

    if record["exception"]:
        log_format = f"{log_format}{{exception}}"

    return log_format


def otel_sink(message) -> None:
    """
    Sinks loguru messages to OpenTelemetry span events.
    """
    span = get_current_span()
    if span != INVALID_SPAN and span.get_span_context().is_valid:
        record = dict(message.record)
        attributes = {
            "log.severity": record["level"].name,
            "log.message": record["message"],
            "code.function": record["function"],
            "code.filepath": record["file"].path,
            "code.lineno": record["line"],
        }
        if record["exception"]:
            attributes["exception.stacktrace"] = str(record["exception"])
        span.add_event(record["message"][:100], attributes=attributes)


def configure_logging() -> None:  # pragma: no cover
    """Configures logging."""
    intercept_handler = InterceptHandler()

    logging.basicConfig(handlers=[intercept_handler], level=logging.NOTSET)

    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith("uvicorn."):
            logging.getLogger(logger_name).handlers = []

    # change handler for default uvicorn logger
    logging.getLogger("uvicorn").handlers = [intercept_handler]
    logging.getLogger("uvicorn.access").handlers = [intercept_handler]

    # set logs output, level and format
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level.value,
        format=record_formatter,
    )

    # send log statements to OpenTelemetry span events
    logger.add(
        otel_sink,
        level=settings.log_level.value,
    )

    # Silence httpx / httpcore built-in request logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
