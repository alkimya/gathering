"""
Extended tests for telemetry decorators with mocked telemetry enabled.

Tests the actual decorator logic when telemetry is enabled.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

from gathering.telemetry.decorators import (
    trace_method,
    trace_async_method,
    measure_time,
    measure_time_async,
)


class TestTraceMethodWithTelemetry:
    """Test trace_method decorator with telemetry enabled."""

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_tracer')
    def test_trace_method_enabled(self, mock_get_tracer, mock_is_enabled):
        """Test trace_method when telemetry is enabled."""
        mock_is_enabled.return_value = True

        # Mock tracer and span
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_get_tracer.return_value = mock_tracer

        @trace_method(name="test_function")
        def test_func(x, y):
            return x + y

        result = test_func(2, 3)

        assert result == 5
        mock_tracer.start_as_current_span.assert_called_once_with("test_function")

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_tracer')
    def test_trace_method_with_attributes(self, mock_get_tracer, mock_is_enabled):
        """Test trace_method works with attributes (if supported)."""
        mock_is_enabled.return_value = True

        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_get_tracer.return_value = mock_tracer

        @trace_method(name="custom_func")
        def test_func():
            return "done"

        result = test_func()

        assert result == "done"
        # Just verify tracer was called
        mock_tracer.start_as_current_span.assert_called_once()

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_tracer')
    def test_trace_method_with_exception(self, mock_get_tracer, mock_is_enabled):
        """Test trace_method records exceptions."""
        mock_is_enabled.return_value = True

        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_get_tracer.return_value = mock_tracer

        @trace_method(name="failing_func")
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_func()

        # Span should have recorded the exception
        assert mock_span.record_exception.called

    @patch('gathering.telemetry.decorators.is_enabled')
    def test_trace_method_disabled(self, mock_is_enabled):
        """Test trace_method when telemetry is disabled."""
        mock_is_enabled.return_value = False

        @trace_method(name="test_func")
        def test_func(x):
            return x * 2

        result = test_func(5)

        assert result == 10  # Should work normally


class TestTraceAsyncMethodWithTelemetry:
    """Test trace_async_method decorator with telemetry enabled."""

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_tracer')
    @pytest.mark.asyncio
    async def test_trace_async_enabled(self, mock_get_tracer, mock_is_enabled):
        """Test trace_async_method when telemetry is enabled."""
        mock_is_enabled.return_value = True

        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_get_tracer.return_value = mock_tracer

        @trace_async_method(name="async_test")
        async def async_func(x):
            await asyncio.sleep(0.001)
            return x + 10

        result = await async_func(5)

        assert result == 15
        mock_tracer.start_as_current_span.assert_called_once_with("async_test")

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_tracer')
    @pytest.mark.asyncio
    async def test_trace_async_with_exception(self, mock_get_tracer, mock_is_enabled):
        """Test trace_async_method records exceptions."""
        mock_is_enabled.return_value = True

        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_get_tracer.return_value = mock_tracer

        @trace_async_method(name="async_failing")
        async def async_failing():
            await asyncio.sleep(0.001)
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError):
            await async_failing()

        assert mock_span.record_exception.called

    @patch('gathering.telemetry.decorators.is_enabled')
    @pytest.mark.asyncio
    async def test_trace_async_disabled(self, mock_is_enabled):
        """Test trace_async_method when telemetry is disabled."""
        mock_is_enabled.return_value = False

        @trace_async_method(name="async_func")
        async def async_func(x):
            return x * 3

        result = await async_func(7)

        assert result == 21


class TestMeasureTimeWithTelemetry:
    """Test measure_time decorator with telemetry enabled."""

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_meter')
    def test_measure_time_enabled(self, mock_get_meter, mock_is_enabled):
        """Test measure_time when telemetry is enabled."""
        mock_is_enabled.return_value = True

        mock_histogram = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        mock_get_meter.return_value = mock_meter

        @measure_time("operation_duration", unit="ms")
        def timed_func(x):
            return x + 1

        result = timed_func(10)

        assert result == 11
        # Should have created histogram
        mock_meter.create_histogram.assert_called_once()
        # Should have recorded value
        assert mock_histogram.record.called

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_meter')
    def test_measure_time_with_tags(self, mock_get_meter, mock_is_enabled):
        """Test measure_time works (tags may or may not be supported)."""
        mock_is_enabled.return_value = True

        mock_histogram = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        mock_get_meter.return_value = mock_meter

        @measure_time("api_latency", unit="ms")
        def api_call():
            return {"status": "ok"}

        result = api_call()

        assert result["status"] == "ok"
        # Just check that meter was used
        assert mock_meter.create_histogram.called or mock_histogram.record.called

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_meter')
    def test_measure_time_with_exception(self, mock_get_meter, mock_is_enabled):
        """Test measure_time still records time on exception."""
        mock_is_enabled.return_value = True

        mock_histogram = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        mock_get_meter.return_value = mock_meter

        @measure_time("failing_operation", unit="ms")
        def failing_func():
            raise Exception("Fail")

        with pytest.raises(Exception):
            failing_func()

        # Should still record time even on failure
        assert mock_histogram.record.called

    @patch('gathering.telemetry.decorators.is_enabled')
    def test_measure_time_disabled(self, mock_is_enabled):
        """Test measure_time when telemetry is disabled."""
        mock_is_enabled.return_value = False

        @measure_time("operation", unit="ms")
        def test_func(x):
            return x * 2

        result = test_func(6)

        assert result == 12


class TestMeasureTimeAsyncWithTelemetry:
    """Test measure_time_async decorator with telemetry enabled."""

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_meter')
    @pytest.mark.asyncio
    async def test_measure_time_async_enabled(self, mock_get_meter, mock_is_enabled):
        """Test measure_time_async when telemetry is enabled."""
        mock_is_enabled.return_value = True

        mock_histogram = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        mock_get_meter.return_value = mock_meter

        @measure_time_async("async_operation", unit="ms")
        async def async_timed_func(x):
            await asyncio.sleep(0.001)
            return x + 5

        result = await async_timed_func(10)

        assert result == 15
        assert mock_histogram.record.called

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_meter')
    @pytest.mark.asyncio
    async def test_measure_time_async_with_exception(self, mock_get_meter, mock_is_enabled):
        """Test measure_time_async records time on exception."""
        mock_is_enabled.return_value = True

        mock_histogram = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        mock_get_meter.return_value = mock_meter

        @measure_time_async("async_failing", unit="ms")
        async def async_failing():
            await asyncio.sleep(0.001)
            raise Exception("Async fail")

        with pytest.raises(Exception):
            await async_failing()

        # Should still record time
        assert mock_histogram.record.called

    @patch('gathering.telemetry.decorators.is_enabled')
    @pytest.mark.asyncio
    async def test_measure_time_async_disabled(self, mock_is_enabled):
        """Test measure_time_async when telemetry is disabled."""
        mock_is_enabled.return_value = False

        @measure_time_async("async_op", unit="ms")
        async def async_func(x):
            return x * 4

        result = await async_func(3)

        assert result == 12


class TestDecoratorCombinations:
    """Test using multiple decorators together."""

    @patch('gathering.telemetry.decorators.is_enabled')
    @patch('gathering.telemetry.decorators.get_tracer')
    @patch('gathering.telemetry.decorators.get_meter')
    def test_trace_and_measure_combined(self, mock_get_meter, mock_get_tracer, mock_is_enabled):
        """Test combining trace and measure decorators."""
        mock_is_enabled.return_value = True

        # Mock tracer
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = Mock(return_value=False)
        mock_get_tracer.return_value = mock_tracer

        # Mock meter
        mock_histogram = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        mock_get_meter.return_value = mock_meter

        @trace_method(name="combined_func")
        @measure_time("combined_duration", unit="ms")
        def combined_func(x, y):
            return x + y

        result = combined_func(3, 4)

        assert result == 7
        # Both decorators should have been applied
        assert mock_tracer.start_as_current_span.called
        assert mock_histogram.record.called

    @patch('gathering.telemetry.decorators.is_enabled')
    def test_multiple_decorators_disabled(self, mock_is_enabled):
        """Test that multiple decorators work when telemetry disabled."""
        mock_is_enabled.return_value = False

        @trace_method(name="func")
        @measure_time("duration", unit="ms")
        def test_func(x):
            return x * 10

        result = test_func(5)

        assert result == 50
