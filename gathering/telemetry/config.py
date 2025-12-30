"""
OpenTelemetry configuration and setup.

Provides:
- Tracer setup (Jaeger export)
- Meter setup (Prometheus export)
- Resource configuration
- Graceful degradation
"""

import os
from dataclasses import dataclass
from typing import Optional, Any

# Optional OpenTelemetry imports
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    metrics = None
    TracerProvider = None
    MeterProvider = None


@dataclass
class TelemetryConfig:
    """Configuration for OpenTelemetry."""

    # General
    enabled: bool = True
    service_name: str = "gathering"
    environment: str = "development"

    # Tracing
    tracing_enabled: bool = True
    otlp_endpoint: str = "http://localhost:4317"  # Jaeger OTLP

    # Metrics
    metrics_enabled: bool = True
    metrics_export_interval: int = 60  # seconds

    # Sampling
    trace_sample_rate: float = 1.0  # 100% (reduce in production)

    # Auto-instrumentation
    instrument_requests: bool = True
    instrument_httpx: bool = True


# Global tracer and meter (use Any to avoid type issues when OTel not available)
_tracer: Optional[Any] = None
_meter: Optional[Any] = None
_telemetry_enabled: bool = False


def setup_telemetry(config: Optional[TelemetryConfig] = None) -> bool:
    """
    Setup OpenTelemetry tracing and metrics.

    Args:
        config: Telemetry configuration (defaults from env if None).

    Returns:
        True if telemetry was successfully initialized.
    """
    global _tracer, _meter, _telemetry_enabled

    # Use default config if not provided
    if config is None:
        config = TelemetryConfig.from_env()

    # Check if enabled
    if not config.enabled or not OTEL_AVAILABLE:
        print("[Telemetry] Disabled or OpenTelemetry not available")
        _telemetry_enabled = False
        return False

    try:
        # Create resource
        resource = Resource(attributes={
            SERVICE_NAME: config.service_name,
            "environment": config.environment,
        })

        # Setup tracing
        if config.tracing_enabled:
            trace_provider = TracerProvider(resource=resource)

            # OTLP exporter (Jaeger)
            otlp_exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace_provider.add_span_processor(span_processor)

            # Set global tracer provider
            trace.set_tracer_provider(trace_provider)
            _tracer = trace.get_tracer(__name__)

            print(f"[Telemetry] Tracing enabled → {config.otlp_endpoint}")

        # Setup metrics
        if config.metrics_enabled:
            metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=config.otlp_endpoint),
                export_interval_millis=config.metrics_export_interval * 1000,
            )
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader],
            )

            # Set global meter provider
            metrics.set_meter_provider(meter_provider)
            _meter = metrics.get_meter(__name__)

            print(f"[Telemetry] Metrics enabled → {config.otlp_endpoint}")

        # Auto-instrumentation
        if config.instrument_requests:
            RequestsInstrumentor().instrument()
            print("[Telemetry] Requests instrumentation enabled")

        if config.instrument_httpx:
            HTTPXClientInstrumentor().instrument()
            print("[Telemetry] HTTPX instrumentation enabled")

        _telemetry_enabled = True
        return True

    except Exception as e:
        print(f"[Telemetry] Setup failed: {e}")
        print("[Telemetry] Running without telemetry (degraded mode)")
        _telemetry_enabled = False
        return False


@classmethod
def from_env(cls) -> "TelemetryConfig":
    """
    Create config from environment variables.

    Environment variables:
    - TELEMETRY_ENABLED: Enable telemetry (default: true)
    - TELEMETRY_SERVICE_NAME: Service name (default: gathering)
    - TELEMETRY_ENVIRONMENT: Environment (default: development)
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (default: http://localhost:4317)
    - TELEMETRY_TRACE_SAMPLE_RATE: Sampling rate (default: 1.0)

    Returns:
        Configured TelemetryConfig.
    """
    return cls(
        enabled=os.getenv("TELEMETRY_ENABLED", "true").lower() == "true",
        service_name=os.getenv("TELEMETRY_SERVICE_NAME", "gathering"),
        environment=os.getenv("TELEMETRY_ENVIRONMENT", "development"),
        otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        trace_sample_rate=float(os.getenv("TELEMETRY_TRACE_SAMPLE_RATE", "1.0")),
    )


# Add from_env as class method
TelemetryConfig.from_env = from_env


def get_tracer(name: str = __name__) -> Optional[Any]:
    """
    Get tracer instance.

    Args:
        name: Tracer name (usually __name__).

    Returns:
        Tracer if enabled, None otherwise.
    """
    if not _telemetry_enabled or not OTEL_AVAILABLE:
        return None

    return trace.get_tracer(name)


def get_meter(name: str = __name__) -> Optional[Any]:
    """
    Get meter instance.

    Args:
        name: Meter name (usually __name__).

    Returns:
        Meter if enabled, None otherwise.
    """
    if not _telemetry_enabled or not OTEL_AVAILABLE:
        return None

    return metrics.get_meter(name)


def is_enabled() -> bool:
    """Check if telemetry is enabled and working."""
    return _telemetry_enabled
