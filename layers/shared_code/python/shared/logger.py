"""
Structured logging utilities for PromoTracker.
"""
import json
import logging
from typing import Any, Dict


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger with JSON formatting.

    Args:
        name: Logger name

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


class JsonFormatter(logging.Formatter):
    """JSON formatter for CloudWatch logs."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON formatted log string
        """
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)
