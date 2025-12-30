"""
Custom metrics for GatheRing observability.

Provides metrics for:
- Agent operations
- LLM calls
- Tool executions
- Event bus activity
- Cache performance
"""

from typing import Optional, Dict, Any

from gathering.telemetry.config import get_meter, is_enabled


class AgentMetrics:
    """Metrics for agent operations."""

    def __init__(self):
        self._meter = get_meter(__name__)
        self._enabled = is_enabled()

        if self._enabled and self._meter:
            # Agent operation metrics
            self.run_duration = self._meter.create_histogram(
                name="agent.run.duration",
                unit="ms",
                description="Duration of agent.run() calls",
            )

            self.tool_call_duration = self._meter.create_histogram(
                name="agent.tool_call.duration",
                unit="ms",
                description="Duration of tool executions",
            )

            self.tool_call_counter = self._meter.create_counter(
                name="agent.tool_calls.total",
                description="Total number of tool calls",
            )

            self.tool_call_errors = self._meter.create_counter(
                name="agent.tool_calls.errors",
                description="Total number of tool call errors",
            )

            # Response metrics
            self.tokens_used = self._meter.create_histogram(
                name="agent.tokens.used",
                description="Tokens used per response",
            )

            self.iterations = self._meter.create_histogram(
                name="agent.iterations",
                description="Number of iterations per run",
            )

    def record_run_duration(self, duration_ms: float, agent_id: int, success: bool = True):
        """Record agent run duration."""
        if self._enabled and self.run_duration:
            self.run_duration.record(
                duration_ms,
                attributes={
                    "agent_id": str(agent_id),
                    "success": str(success),
                }
            )

    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool = True,
        agent_id: Optional[int] = None,
    ):
        """Record tool call metrics."""
        if not self._enabled:
            return

        attributes = {
            "tool_name": tool_name,
            "success": str(success),
        }
        if agent_id:
            attributes["agent_id"] = str(agent_id)

        if self.tool_call_duration:
            self.tool_call_duration.record(duration_ms, attributes=attributes)

        if self.tool_call_counter:
            self.tool_call_counter.add(1, attributes=attributes)

        if not success and self.tool_call_errors:
            self.tool_call_errors.add(1, attributes=attributes)

    def record_tokens(self, tokens: int, model: str, agent_id: Optional[int] = None):
        """Record token usage."""
        if self._enabled and self.tokens_used:
            attributes = {"model": model}
            if agent_id:
                attributes["agent_id"] = str(agent_id)

            self.tokens_used.record(tokens, attributes=attributes)

    def record_iterations(self, iterations: int, agent_id: Optional[int] = None):
        """Record iteration count."""
        if self._enabled and self.iterations:
            attributes = {}
            if agent_id:
                attributes["agent_id"] = str(agent_id)

            self.iterations.record(iterations, attributes=attributes)


class LLMMetrics:
    """Metrics for LLM operations."""

    def __init__(self):
        self._meter = get_meter(__name__)
        self._enabled = is_enabled()

        if self._enabled and self._meter:
            # LLM call metrics
            self.llm_call_duration = self._meter.create_histogram(
                name="llm.call.duration",
                unit="ms",
                description="Duration of LLM API calls",
            )

            self.llm_call_counter = self._meter.create_counter(
                name="llm.calls.total",
                description="Total number of LLM calls",
            )

            self.llm_call_errors = self._meter.create_counter(
                name="llm.calls.errors",
                description="Total number of LLM call errors",
            )

            self.llm_tokens_prompt = self._meter.create_histogram(
                name="llm.tokens.prompt",
                description="Tokens in prompt",
            )

            self.llm_tokens_completion = self._meter.create_histogram(
                name="llm.tokens.completion",
                description="Tokens in completion",
            )

    def record_llm_call(
        self,
        provider: str,
        model: str,
        duration_ms: float,
        success: bool = True,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ):
        """Record LLM call metrics."""
        if not self._enabled:
            return

        attributes = {
            "provider": provider,
            "model": model,
            "success": str(success),
        }

        if self.llm_call_duration:
            self.llm_call_duration.record(duration_ms, attributes=attributes)

        if self.llm_call_counter:
            self.llm_call_counter.add(1, attributes=attributes)

        if not success and self.llm_call_errors:
            self.llm_call_errors.add(1, attributes=attributes)

        if success:
            if prompt_tokens and self.llm_tokens_prompt:
                self.llm_tokens_prompt.record(prompt_tokens, attributes=attributes)

            if completion_tokens and self.llm_tokens_completion:
                self.llm_tokens_completion.record(completion_tokens, attributes=attributes)


class EventBusMetrics:
    """Metrics for Event Bus operations."""

    def __init__(self):
        self._meter = get_meter(__name__)
        self._enabled = is_enabled()

        if self._enabled and self._meter:
            # Event metrics
            self.events_published = self._meter.create_counter(
                name="eventbus.events.published",
                description="Total events published",
            )

            self.events_delivered = self._meter.create_counter(
                name="eventbus.events.delivered",
                description="Total events delivered to handlers",
            )

            self.handler_errors = self._meter.create_counter(
                name="eventbus.handler.errors",
                description="Total handler errors",
            )

            self.handler_duration = self._meter.create_histogram(
                name="eventbus.handler.duration",
                unit="ms",
                description="Handler execution duration",
            )

    def record_event_published(self, event_type: str):
        """Record event publication."""
        if self._enabled and self.events_published:
            self.events_published.add(1, attributes={"event_type": event_type})

    def record_event_delivered(self, event_type: str, handler_count: int):
        """Record event delivery."""
        if self._enabled and self.events_delivered:
            self.events_delivered.add(
                handler_count,
                attributes={"event_type": event_type}
            )

    def record_handler_error(self, event_type: str):
        """Record handler error."""
        if self._enabled and self.handler_errors:
            self.handler_errors.add(1, attributes={"event_type": event_type})

    def record_handler_duration(self, event_type: str, duration_ms: float):
        """Record handler duration."""
        if self._enabled and self.handler_duration:
            self.handler_duration.record(
                duration_ms,
                attributes={"event_type": event_type}
            )


class CacheMetrics:
    """Metrics for cache operations."""

    def __init__(self):
        self._meter = get_meter(__name__)
        self._enabled = is_enabled()

        if self._enabled and self._meter:
            # Cache hit/miss
            self.cache_hits = self._meter.create_counter(
                name="cache.hits",
                description="Total cache hits",
            )

            self.cache_misses = self._meter.create_counter(
                name="cache.misses",
                description="Total cache misses",
            )

            # Cache operation duration
            self.cache_op_duration = self._meter.create_histogram(
                name="cache.operation.duration",
                unit="ms",
                description="Cache operation duration",
            )

    def record_cache_hit(self, cache_type: str):
        """Record cache hit."""
        if self._enabled and self.cache_hits:
            self.cache_hits.add(1, attributes={"cache_type": cache_type})

    def record_cache_miss(self, cache_type: str):
        """Record cache miss."""
        if self._enabled and self.cache_misses:
            self.cache_misses.add(1, attributes={"cache_type": cache_type})

    def record_cache_operation(self, operation: str, duration_ms: float, cache_type: str):
        """Record cache operation duration."""
        if self._enabled and self.cache_op_duration:
            self.cache_op_duration.record(
                duration_ms,
                attributes={
                    "operation": operation,
                    "cache_type": cache_type,
                }
            )


# Global metric instances
agent_metrics = AgentMetrics()
llm_metrics = LLMMetrics()
eventbus_metrics = EventBusMetrics()
cache_metrics = CacheMetrics()
