"""
Telemetry decorators for tracing and metrics.

Provides easy-to-use decorators for:
- Method tracing
- Async method tracing
- Time measurement
- Custom attributes
"""

import functools
import time
from typing import Callable, Any, Optional, Dict

from gathering.telemetry.config import get_tracer, get_meter, is_enabled


def trace_method(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Decorator to trace a synchronous method.

    Args:
        name: Span name (defaults to function name).
        attributes: Additional span attributes.

    Example:
        @trace_method(name="process_task", attributes={"task_type": "analysis"})
        def process_task(self, task_id):
            # ... processing ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if telemetry is enabled
            if not is_enabled():
                return func(*args, **kwargs)

            tracer = get_tracer(func.__module__)
            if tracer is None:
                return func(*args, **kwargs)

            # Create span
            span_name = name or f"{func.__qualname__}"

            with tracer.start_as_current_span(span_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # Add function arguments as attributes
                if args and hasattr(args[0], "__class__"):
                    span.set_attribute("class", args[0].__class__.__name__)

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator


def trace_async_method(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Decorator to trace an asynchronous method.

    Args:
        name: Span name (defaults to function name).
        attributes: Additional span attributes.

    Example:
        @trace_async_method(name="fetch_data")
        async def fetch_data(self, url):
            # ... async operation ...
            return data
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if telemetry is enabled
            if not is_enabled():
                return await func(*args, **kwargs)

            tracer = get_tracer(func.__module__)
            if tracer is None:
                return await func(*args, **kwargs)

            # Create span
            span_name = name or f"{func.__qualname__}"

            with tracer.start_as_current_span(span_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # Add function arguments as attributes
                if args and hasattr(args[0], "__class__"):
                    span.set_attribute("class", args[0].__class__.__name__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper
    return decorator


def measure_time(metric_name: str, unit: str = "ms"):
    """
    Decorator to measure execution time and record as metric.

    Args:
        metric_name: Name of the metric.
        unit: Time unit (ms, s).

    Example:
        @measure_time("task_duration", unit="ms")
        def process_task(self, task_id):
            # ... processing ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if telemetry is enabled
            if not is_enabled():
                return func(*args, **kwargs)

            meter = get_meter(func.__module__)
            if meter is None:
                return func(*args, **kwargs)

            # Create histogram
            histogram = meter.create_histogram(
                name=metric_name,
                unit=unit,
                description=f"Duration of {func.__qualname__}",
            )

            # Measure time
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time

                # Convert to requested unit
                if unit == "ms":
                    duration *= 1000
                elif unit == "s":
                    pass  # Already in seconds
                else:
                    raise ValueError(f"Unsupported unit: {unit}")

                # Record metric
                attributes = {}
                if args and hasattr(args[0], "__class__"):
                    attributes["class"] = args[0].__class__.__name__

                histogram.record(duration, attributes=attributes)

        return wrapper
    return decorator


def measure_time_async(metric_name: str, unit: str = "ms"):
    """
    Decorator to measure async execution time and record as metric.

    Args:
        metric_name: Name of the metric.
        unit: Time unit (ms, s).

    Example:
        @measure_time_async("llm_call_duration", unit="ms")
        async def call_llm(self, prompt):
            # ... async LLM call ...
            return response
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if telemetry is enabled
            if not is_enabled():
                return await func(*args, **kwargs)

            meter = get_meter(func.__module__)
            if meter is None:
                return await func(*args, **kwargs)

            # Create histogram
            histogram = meter.create_histogram(
                name=metric_name,
                unit=unit,
                description=f"Duration of {func.__qualname__}",
            )

            # Measure time
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time

                # Convert to requested unit
                if unit == "ms":
                    duration *= 1000
                elif unit == "s":
                    pass  # Already in seconds
                else:
                    raise ValueError(f"Unsupported unit: {unit}")

                # Record metric
                attributes = {}
                if args and hasattr(args[0], "__class__"):
                    attributes["class"] = args[0].__class__.__name__

                histogram.record(duration, attributes=attributes)

        return wrapper
    return decorator
