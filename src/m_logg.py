"""Simple Loguru setup with Streamlit integration - MVP approach."""

import functools
import logging
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import Any

import streamlit as st
from loguru import logger


def setup_logging(log_level: str = "INFO") -> None:
    """Setup minimal but effective logging with Streamlit cache protection.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Check if already setup to avoid re-configuration
    if "logging_configured" in st.session_state and st.session_state.logging_configured:
        return

    # Remove default handler
    logger.remove()

    # Console output - clean format
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {name}:{function}:{line} | {message}",
        level=log_level,
        colorize=True,
    )

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Simple file logging with rotation
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )

    # Intercept standard library logging (untuk Streamlit) - Simplified
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            """Emit a log record by redirecting to loguru.

            Args:
                record: The log record to emit
            """
            # Simplified approach - avoid internal access
            try:
                level = record.levelname
            except Exception:
                level = "INFO"

            # Use public API only
            logger.log(level, record.getMessage())

    # Replace standard logging with Loguru - safer approach
    logging.getLogger().handlers = [InterceptHandler()]
    logging.getLogger().setLevel(logging.DEBUG)

    # Mark as configured
    st.session_state.logging_configured = True
    logger.info(
        f"Logging configured with level {log_level}. Use logger_wraps, timer, lazy_log, or LogContext for enhanced logging."
    )


def logger_wraps(*, entry: bool = True, exit: bool = True, level: str = "DEBUG"):
    """Decorator to log entry and exit of functions.

    Usage:
        @logger_wraps()
        def my_function(a, b):
            return a + b

        @logger_wraps(entry=False, level="INFO")
        def only_exit_log():
            return "result"
    """

    def wrapper(func: Callable) -> Callable:
        name = func.__name__

        @functools.wraps(func)
        def wrapped(*args, **kwargs) -> Any:
            # Avoid internal opt() usage - use direct logging
            if entry:
                logger.log(
                    level, f"Entering '{name}' (args={len(args)}, kwargs={len(kwargs)})"
                )

            result = func(*args, **kwargs)

            if exit:
                logger.log(level, f"Exiting '{name}' (completed)")

            return result

        return wrapped

    return wrapper


def timer(operation: str | None = None):
    """Decorator to log execution time.

    Usage:
        @timer("CSV_IMPORT")
        def import_csv():
            pass

        @timer()  # Will use function name
        def process_data():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            op_name = operation or func.__name__.upper()
            start = time.perf_counter()

            try:
                logger.info(f"[{op_name}] Starting...")
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger.info(f"[{op_name}] Completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                logger.error(f"[{op_name}] Failed after {duration:.3f}s: {e}")
                raise

        return wrapper

    return decorator


def lazy_log(level: str = "INFO"):
    """Lazy logging decorator - only logs if enabled.

    Simplified version without internal API access.

    Usage:
        @lazy_log("DEBUG")
        def debug_function():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Simplified check - just log if needed
            if level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                logger.log(
                    level,
                    f"Calling {func.__name__} with {len(args)} args, {len(kwargs)} kwargs",
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator


class LogContext:
    """Context manager for logging operations.

    Usage:
        with LogContext("PROCESSING_CSV"):
            # your code here
            pass
    """

    def __init__(self, operation: str, level: str = "INFO"):
        self.operation = operation
        self.level = level
        self.start_time: float | None = None

    def __enter__(self) -> "LogContext":
        """Enter the context manager and start timing.

        Returns:
            Self for context management
        """
        self.start_time = time.perf_counter()
        logger.log(self.level, f"[{self.operation}] Starting...")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager and log completion or failure.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        if self.start_time is None:
            return

        duration = time.perf_counter() - self.start_time
        if exc_type:
            logger.error(f"[{self.operation}] Failed after {duration:.3f}s: {exc_val}")
        else:
            logger.log(self.level, f"[{self.operation}] Completed in {duration:.3f}s")


def exception_handler(func: Callable) -> Callable:
    """Decorator to automatically log exceptions with context.

    Usage:
        @exception_handler
        def create_partner(data):
            return Partner(**data)  # Will log ValidationError automatically
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log exception with context
            logger.error(
                f"Exception in {func.__name__}: {type(e).__name__}: {e}",
                extra={
                    "function": func.__name__,
                    "exception_type": type(e).__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()) if kwargs else [],
                },
            )
            # Re-raise for proper error handling upstream
            raise

    return wrapper


def validation_logger(model_name: str):
    """Specific decorator for model validation logging.

    Usage:
        @validation_logger("Partner")
        def create_partner(data):
            return Partner(**data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                logger.debug(f"Validating {model_name} with data: {kwargs}")
                result = func(*args, **kwargs)
                logger.info(f"{model_name} validation successful")
                return result
            except ValueError as e:
                logger.warning(f"{model_name} validation failed: {e}")
                raise
            except Exception as e:
                logger.error(f"{model_name} unexpected error: {type(e).__name__}: {e}")
                raise

        return wrapper

    return decorator


def performance_monitor(threshold_seconds: float = 1.0):
    """Decorator to monitor function performance and warn if too slow.

    Args:
        threshold_seconds: Time threshold to trigger warning

    Usage:
        @performance_monitor(0.5)  # Warn if takes > 0.5s
        def slow_function():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start

            if duration > threshold_seconds:
                logger.warning(
                    f"Performance warning: {func.__name__} took {duration:.3f}s "
                    f"(threshold: {threshold_seconds}s)"
                )
            else:
                logger.debug(f"{func.__name__} completed in {duration:.3f}s")

            return result

        return wrapper

    return decorator


def log_dataframe_info(df_name: str = "DataFrame"):
    """Decorator to log pandas DataFrame information.

    Args:
        df_name: Name to use in log messages

    Usage:
        @log_dataframe_info("Customer_Data")
        def process_customers(df):
            return df
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)

            # Check if result looks like a DataFrame
            if hasattr(result, "shape") and hasattr(result, "dtypes"):
                logger.info(
                    f"{df_name} info: {result.shape[0]} rows, {result.shape[1]} columns"
                )
                logger.debug(f"{df_name} columns: {list(result.columns)}")

            return result

        return wrapper

    return decorator


def database_operation_logger(operation_type: str):
    """Decorator for logging database operations.

    Args:
        operation_type: Type of operation (INSERT, UPDATE, DELETE, SELECT)

    Usage:
        @database_operation_logger("INSERT")
        def create_organization(data):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger.info(f"DB {operation_type}: Starting {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.info(
                    f"DB {operation_type}: {func.__name__} completed successfully"
                )
                return result
            except Exception as e:
                logger.error(f"DB {operation_type}: {func.__name__} failed - {e}")
                raise

        return wrapper

    return decorator


def streamlit_cache_logger(cache_type: str = "data"):
    """Decorator to log Streamlit cache operations.

    Args:
        cache_type: Type of cache (data, resource)

    Usage:
        @streamlit_cache_logger("data")
        @st.cache_data
        def load_data():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger.debug(f"Cache {cache_type}: Checking cache for {func.__name__}")
            result = func(*args, **kwargs)
            logger.debug(
                f"Cache {cache_type}: {func.__name__} cache operation completed"
            )
            return result

        return wrapper

    return decorator


def business_rule_logger(rule_name: str):
    """Decorator for logging business rule validations.

    Args:
        rule_name: Name of the business rule

    Usage:
        @business_rule_logger("Partner_Status_Check")
        def validate_partner_status(partner):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger.info(f"Business Rule: Applying {rule_name}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"Business Rule: {rule_name} passed")
                return result
            except Exception as e:
                logger.warning(f"Business Rule: {rule_name} failed - {e}")
                raise

        return wrapper

    return decorator


def etl_stage_logger(stage: str):
    """Decorator for ETL pipeline stage logging.

    Args:
        stage: ETL stage name (Extract, Transform, Load)

    Usage:
        @etl_stage_logger("Transform")
        def transform_csv_data(df):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger.info(f"ETL {stage}: Starting stage")
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger.info(f"ETL {stage}: Completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                logger.error(f"ETL {stage}: Failed after {duration:.3f}s - {e}")
                raise

        return wrapper

    return decorator


def csv_operation_logger(operation: str):
    """Decorator for CSV file operations.

    Args:
        operation: CSV operation type (read, write, validate)

    Usage:
        @csv_operation_logger("read")
        def read_csv_file(filepath):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger.info(f"CSV {operation}: Starting operation")
            try:
                result = func(*args, **kwargs)
                # Try to log additional info if result is DataFrame-like
                if hasattr(result, "shape"):
                    logger.info(f"CSV {operation}: Processed {result.shape[0]} records")
                else:
                    logger.info(f"CSV {operation}: Operation completed")
                return result
            except Exception as e:
                logger.error(f"CSV {operation}: Failed - {e}")
                raise

        return wrapper

    return decorator


# Export the main logger and utilities
__all__ = [
    "setup_logging",
    "logger_wraps",
    "timer",
    "lazy_log",
    "LogContext",
    "exception_handler",
    "validation_logger",
    "performance_monitor",
    "log_dataframe_info",
    "database_operation_logger",
    "streamlit_cache_logger",
    "business_rule_logger",
    "etl_stage_logger",
    "csv_operation_logger",
    "logger",
]
