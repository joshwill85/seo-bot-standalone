"""Structured logging configuration for SEO-Bot."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.stdlib import LoggerFactory

from .config import settings


def setup_logging(
    log_level: str = None,
    log_format: str = None,
    log_file: Optional[str] = None
) -> None:
    """Configure structured logging for the application."""
    
    level = log_level or settings.log_level
    format_type = log_format or settings.log_format
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # Shared processors for all loggers
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Configure output format
    if format_type == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure the formatter for stdlib logging
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
    )
    
    # Apply formatter to all handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add structured logging to classes."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get a logger for this class."""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


def log_function_call(func_name: str, **kwargs) -> Dict[str, Any]:
    """Create a standardized log entry for function calls."""
    return {
        "event": "function_call",
        "function": func_name,
        **kwargs
    }


def log_api_request(
    service: str,
    endpoint: str,
    method: str = "GET",
    status_code: Optional[int] = None,
    response_time_ms: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create a standardized log entry for API requests."""
    entry = {
        "event": "api_request",
        "service": service,
        "endpoint": endpoint,
        "method": method,
        **kwargs
    }
    
    if status_code is not None:
        entry["status_code"] = status_code
    
    if response_time_ms is not None:
        entry["response_time_ms"] = response_time_ms
    
    return entry


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str,
    page_url: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create a standardized log entry for performance metrics."""
    entry = {
        "event": "performance_metric",
        "metric": metric_name,
        "value": value,
        "unit": unit,
        **kwargs
    }
    
    if page_url:
        entry["page_url"] = page_url
    
    return entry


def log_content_action(
    action: str,
    content_type: str,
    title: str,
    slug: str,
    **kwargs
) -> Dict[str, Any]:
    """Create a standardized log entry for content actions."""
    return {
        "event": "content_action",
        "action": action,  # created, updated, published, deleted
        "content_type": content_type,
        "title": title,
        "slug": slug,
        **kwargs
    }


def log_seo_metric(
    metric_name: str,
    value: float,
    page_url: str,
    query: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create a standardized log entry for SEO metrics."""
    entry = {
        "event": "seo_metric",
        "metric": metric_name,
        "value": value,
        "page_url": page_url,
        **kwargs
    }
    
    if query:
        entry["query"] = query
    
    return entry


# Initialize logging on module import
setup_logging()


# Export commonly used loggers
main_logger = get_logger("seo_bot")
api_logger = get_logger("api")
content_logger = get_logger("content")
performance_logger = get_logger("performance")
seo_logger = get_logger("seo")