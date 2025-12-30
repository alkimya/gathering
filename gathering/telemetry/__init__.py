"""
Telemetry - OpenTelemetry monitoring for GatheRing.

Provides observability via:
- Distributed tracing (Jaeger)
- Metrics (Prometheus)
- Automatic instrumentation
- Custom metrics and spans
"""

from gathering.telemetry.config import (
    TelemetryConfig,
    setup_telemetry,
    get_tracer,
    get_meter,
)

from gathering.telemetry.decorators import (
    trace_method,
    trace_async_method,
    measure_time,
)

__all__ = [
    "TelemetryConfig",
    "setup_telemetry",
    "get_tracer",
    "get_meter",
    "trace_method",
    "trace_async_method",
    "measure_time",
]
