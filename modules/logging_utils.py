"""
Logging utilities with correlation ID support for better tracing

This module provides enhanced logging capabilities with request correlation IDs.
"""
import uuid
from typing import Optional
from contextvars import ContextVar
from functools import wraps
from loguru import logger

# Context variable to store correlation ID across async calls
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID"""
    return correlation_id.get()


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context"""
    correlation_id.set(cid)


def with_correlation_id(func):
    """
    Decorator to automatically generate and set correlation ID for a function

    Usage:
        @with_correlation_id
        def my_function():
            logger.info("This will include correlation ID")
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Generate new correlation ID if not present
        if not get_correlation_id():
            cid = generate_correlation_id()
            set_correlation_id(cid)

        # Log function entry
        logger.bind(correlation_id=get_correlation_id()).debug(
            f"Entering {func.__name__}"
        )

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.bind(correlation_id=get_correlation_id()).error(
                f"Error in {func.__name__}: {str(e)}"
            )
            raise
        finally:
            logger.bind(correlation_id=get_correlation_id()).debug(
                f"Exiting {func.__name__}"
            )

    return wrapper


def log_with_context(level: str, message: str, **kwargs):
    """
    Log a message with correlation ID automatically included

    Args:
        level: Log level (info, debug, warning, error, etc.)
        message: Log message
        **kwargs: Additional context to include in the log
    """
    cid = get_correlation_id()
    log_method = getattr(logger.bind(correlation_id=cid), level)
    log_method(message, **kwargs)


class LogContext:
    """Context manager for logging with correlation IDs"""

    def __init__(self, operation: str):
        self.operation = operation
        self.cid = None

    def __enter__(self):
        self.cid = generate_correlation_id()
        set_correlation_id(self.cid)
        logger.bind(correlation_id=self.cid).info(f"Starting operation: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.bind(correlation_id=self.cid).error(
                f"Operation {self.operation} failed: {exc_val}"
            )
        else:
            logger.bind(correlation_id=self.cid).info(
                f"Operation {self.operation} completed successfully"
            )
        return False


# Configure loguru to include correlation ID in format
def configure_logging_with_correlation():
    """
    Configure loguru to automatically include correlation ID in log messages

    Call this at application startup.
    """
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[correlation_id]}</cyan> | <level>{message}</level>",
        level="INFO"
    )
