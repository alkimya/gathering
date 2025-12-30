"""
Tests for OpenTelemetry telemetry module.

Covers:
- Configuration and setup
- Graceful degradation
- Decorators (trace, measure_time)
- Metrics recording
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from gathering.telemetry.config import TelemetryConfig, setup_telemetry, get_tracer, get_meter, is_enabled
from gathering.telemetry.decorators import trace_method, trace_async_method, measure_time, measure_time_async
from gathering.telemetry.metrics import AgentMetrics, LLMMetrics, EventBusMetrics, CacheMetrics


class TestTelemetryConfig:
    """Test TelemetryConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TelemetryConfig()

        assert config.enabled is True
        assert config.service_name == "gathering"
        assert config.environment == "development"
        assert config.tracing_enabled is True
        assert config.metrics_enabled is True
        assert config.otlp_endpoint == "http://localhost:4317"
        assert config.trace_sample_rate == 1.0

    def test_custom_values(self):
        """Test custom configuration."""
        config = TelemetryConfig(
            enabled=False,
            service_name="test-service",
            environment="production",
            otlp_endpoint="http://jaeger:4317",
            trace_sample_rate=0.5,
        )

        assert config.enabled is False
        assert config.service_name == "test-service"
        assert config.environment == "production"
        assert config.otlp_endpoint == "http://jaeger:4317"
        assert config.trace_sample_rate == 0.5

    @patch.dict("os.environ", {
        "TELEMETRY_ENABLED": "false",
        "TELEMETRY_SERVICE_NAME": "my-service",
        "TELEMETRY_ENVIRONMENT": "staging",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://otel:4317",
        "TELEMETRY_TRACE_SAMPLE_RATE": "0.1",
    })
    def test_from_env(self):
        """Test creating config from environment."""
        config = TelemetryConfig.from_env()

        assert config.enabled is False
        assert config.service_name == "my-service"
        assert config.environment == "staging"
        assert config.otlp_endpoint == "http://otel:4317"
        assert config.trace_sample_rate == 0.1


class TestTelemetrySetup:
    """Test telemetry setup and graceful degradation."""

    @patch("gathering.telemetry.config.OTEL_AVAILABLE", False)
    def test_setup_without_otel_library(self):
        """Test setup when OpenTelemetry not available."""
        config = TelemetryConfig()
        result = setup_telemetry(config)

        assert result is False
        assert is_enabled() is False
        assert get_tracer() is None
        assert get_meter() is None

    @patch("gathering.telemetry.config.OTEL_AVAILABLE", False)
    def test_setup_with_disabled_config(self):
        """Test setup with telemetry disabled in config."""
        config = TelemetryConfig(enabled=False)
        result = setup_telemetry(config)

        assert result is False
        assert is_enabled() is False


class TestTraceDecorator:
    """Test trace_method decorator."""

    def test_trace_when_disabled(self):
        """Test that decorator works when telemetry disabled."""

        @trace_method(name="test_function")
        def test_func(value):
            return value * 2

        # Should work normally without telemetry
        result = test_func(5)
        assert result == 10

    def test_trace_with_exception(self):
        """Test that exceptions are properly handled."""

        @trace_method(name="failing_function")
        def failing_func():
            raise ValueError("Test error")

        # Should still raise the exception
        with pytest.raises(ValueError):
            failing_func()


@pytest.mark.asyncio
class TestTraceAsyncDecorator:
    """Test trace_async_method decorator."""

    async def test_trace_async_when_disabled(self):
        """Test that async decorator works when telemetry disabled."""

        @trace_async_method(name="test_async")
        async def test_async_func(value):
            return value * 2

        # Should work normally without telemetry
        result = await test_async_func(5)
        assert result == 10

    async def test_trace_async_with_exception(self):
        """Test that async exceptions are properly handled."""

        @trace_async_method(name="failing_async")
        async def failing_async_func():
            raise ValueError("Test error")

        # Should still raise the exception
        with pytest.raises(ValueError):
            await failing_async_func()


class TestMeasureTimeDecorator:
    """Test measure_time decorator."""

    def test_measure_time_when_disabled(self):
        """Test that measure_time works when telemetry disabled."""

        @measure_time("test_duration", unit="ms")
        def test_func(value):
            return value * 2

        # Should work normally without telemetry
        result = test_func(5)
        assert result == 10


class TestAgentMetrics:
    """Test AgentMetrics class."""

    def test_initialization(self):
        """Test metrics initialization."""
        metrics = AgentMetrics()

        # Should initialize without errors
        assert metrics is not None

    def test_record_run_duration_when_disabled(self):
        """Test recording run duration when telemetry disabled."""
        metrics = AgentMetrics()

        # Should not raise errors
        metrics.record_run_duration(150.5, agent_id=1, success=True)

    def test_record_tool_call_when_disabled(self):
        """Test recording tool call when telemetry disabled."""
        metrics = AgentMetrics()

        # Should not raise errors
        metrics.record_tool_call("fs_read", 25.3, success=True, agent_id=1)

    def test_record_tokens_when_disabled(self):
        """Test recording tokens when telemetry disabled."""
        metrics = AgentMetrics()

        # Should not raise errors
        metrics.record_tokens(1000, model="claude-sonnet-4", agent_id=1)

    def test_record_iterations_when_disabled(self):
        """Test recording iterations when telemetry disabled."""
        metrics = AgentMetrics()

        # Should not raise errors
        metrics.record_iterations(3, agent_id=1)


class TestLLMMetrics:
    """Test LLMMetrics class."""

    def test_initialization(self):
        """Test metrics initialization."""
        metrics = LLMMetrics()

        assert metrics is not None

    def test_record_llm_call_when_disabled(self):
        """Test recording LLM call when telemetry disabled."""
        metrics = LLMMetrics()

        # Should not raise errors
        metrics.record_llm_call(
            provider="anthropic",
            model="claude-sonnet-4",
            duration_ms=350.5,
            success=True,
            prompt_tokens=500,
            completion_tokens=200,
        )


class TestEventBusMetrics:
    """Test EventBusMetrics class."""

    def test_initialization(self):
        """Test metrics initialization."""
        metrics = EventBusMetrics()

        assert metrics is not None

    def test_record_event_published_when_disabled(self):
        """Test recording event publication when telemetry disabled."""
        metrics = EventBusMetrics()

        # Should not raise errors
        metrics.record_event_published("agent.task.completed")

    def test_record_event_delivered_when_disabled(self):
        """Test recording event delivery when telemetry disabled."""
        metrics = EventBusMetrics()

        # Should not raise errors
        metrics.record_event_delivered("agent.task.completed", handler_count=3)

    def test_record_handler_error_when_disabled(self):
        """Test recording handler error when telemetry disabled."""
        metrics = EventBusMetrics()

        # Should not raise errors
        metrics.record_handler_error("agent.task.completed")

    def test_record_handler_duration_when_disabled(self):
        """Test recording handler duration when telemetry disabled."""
        metrics = EventBusMetrics()

        # Should not raise errors
        metrics.record_handler_duration("agent.task.completed", 15.3)


class TestCacheMetrics:
    """Test CacheMetrics class."""

    def test_initialization(self):
        """Test metrics initialization."""
        metrics = CacheMetrics()

        assert metrics is not None

    def test_record_cache_hit_when_disabled(self):
        """Test recording cache hit when telemetry disabled."""
        metrics = CacheMetrics()

        # Should not raise errors
        metrics.record_cache_hit("embedding")

    def test_record_cache_miss_when_disabled(self):
        """Test recording cache miss when telemetry disabled."""
        metrics = CacheMetrics()

        # Should not raise errors
        metrics.record_cache_miss("embedding")

    def test_record_cache_operation_when_disabled(self):
        """Test recording cache operation when telemetry disabled."""
        metrics = CacheMetrics()

        # Should not raise errors
        metrics.record_cache_operation("get", 2.5, "embedding")


class TestGracefulDegradation:
    """Test graceful degradation across all components."""

    def test_decorators_work_without_telemetry(self):
        """Test that all decorators work without telemetry."""

        @trace_method()
        def sync_func(x):
            return x * 2

        @measure_time("test")
        def timed_func(x):
            return x + 1

        # Should all work
        assert sync_func(5) == 10
        assert timed_func(5) == 6

    def test_metrics_work_without_telemetry(self):
        """Test that all metrics work without telemetry."""
        agent_m = AgentMetrics()
        llm_m = LLMMetrics()
        event_m = EventBusMetrics()
        cache_m = CacheMetrics()

        # Should not raise errors
        agent_m.record_run_duration(100, agent_id=1)
        llm_m.record_llm_call("anthropic", "claude", 200, success=True)
        event_m.record_event_published("test")
        cache_m.record_cache_hit("embedding")
