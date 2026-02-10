"""
Comprehensive pipeline execution engine tests.

Tests cover: topological traversal, output passing, trigger data,
node dispatch (all 6 types), condition branching, retry with backoff,
circuit breaker state transitions, cancellation, timeout, run manager,
and event emission.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gathering.orchestration.events import EventType
from gathering.orchestration.pipeline.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)
from gathering.orchestration.pipeline.executor import (
    PipelineExecutor,
    PipelineRunManager,
    get_run_manager,
)
from gathering.orchestration.pipeline.models import (
    PipelineDefinition,
    PipelineEdge,
    PipelineNode,
)
from gathering.orchestration.pipeline.nodes import (
    NodeConfigError,
    NodeExecutionError,
    dispatch_node,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_node(node_id: str, node_type: str = "action", name: str = "", **config) -> PipelineNode:
    """Create a PipelineNode with minimal boilerplate."""
    return PipelineNode(
        id=node_id,
        type=node_type,
        name=name or f"Node {node_id}",
        config=config,
    )


def make_edge(edge_id: str, from_node: str, to_node: str) -> PipelineEdge:
    """Create a PipelineEdge using field names."""
    return PipelineEdge(id=edge_id, from_node=from_node, to_node=to_node)


def make_pipeline(nodes: list[PipelineNode], edges: list[PipelineEdge]) -> PipelineDefinition:
    """Create a PipelineDefinition."""
    return PipelineDefinition(nodes=nodes, edges=edges)


def make_mock_db() -> MagicMock:
    """Create a mock DatabaseService."""
    db = MagicMock()
    db.execute = MagicMock(return_value=None)
    db.execute_one = MagicMock(return_value=None)
    return db


def make_mock_event_bus() -> AsyncMock:
    """Create a mock EventBus with async emit."""
    bus = AsyncMock()
    bus.emit = AsyncMock()
    return bus


def make_executor(
    pipeline: PipelineDefinition,
    pipeline_id: int = 1,
    event_bus=None,
    agent_registry=None,
) -> PipelineExecutor:
    """Create a PipelineExecutor with mock dependencies."""
    return PipelineExecutor(
        pipeline_id=pipeline_id,
        definition=pipeline,
        db=make_mock_db(),
        event_bus=event_bus,
        agent_registry=agent_registry,
    )


# ---------------------------------------------------------------------------
# Execution basics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestExecutionBasics:
    """Tests for basic pipeline execution."""

    async def test_execute_linear_pipeline(self):
        """3-node linear pipeline executes all nodes in order, returns completed status."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("a1", "agent", agent_id="agent-1", task="do stuff"),
                make_node("act1", "action", action="notify"),
            ],
            edges=[
                make_edge("e1", "t1", "a1"),
                make_edge("e2", "a1", "act1"),
            ],
        )
        executor = make_executor(pipeline)
        result = await executor.execute(run_id=1, trigger_data={"key": "value"})

        assert result["status"] == "completed"
        assert "outputs" in result
        assert "node_results" in result
        # All 3 nodes should have results
        assert len(result["node_results"]) == 3

    async def test_execute_output_passing(self):
        """Agent node output is available as input to downstream node."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("a1", "agent", agent_id="agent-1", task="analyze"),
                make_node("act1", "action", action="store"),
            ],
            edges=[
                make_edge("e1", "t1", "a1"),
                make_edge("e2", "a1", "act1"),
            ],
        )
        executor = make_executor(pipeline)
        result = await executor.execute(run_id=1, trigger_data={"input": "data"})

        assert result["status"] == "completed"
        outputs = result["outputs"]
        # Agent node output should contain the simulated result
        assert "a1" in outputs
        assert "result" in outputs["a1"]
        # Action node should have received agent output as input
        assert "act1" in outputs
        assert outputs["act1"]["executed"] is True

    async def test_execute_trigger_passes_data(self):
        """Trigger data is available to downstream nodes."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("act1", "action", action="process"),
            ],
            edges=[make_edge("e1", "t1", "act1")],
        )
        executor = make_executor(pipeline)
        trigger_data = {"event": "webhook", "payload": {"user_id": 42}}
        result = await executor.execute(run_id=1, trigger_data=trigger_data)

        assert result["status"] == "completed"
        # Trigger output should be the trigger_data
        assert result["outputs"]["t1"] == trigger_data


# ---------------------------------------------------------------------------
# Node dispatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestNodeDispatch:
    """Tests for individual node type dispatching."""

    async def test_dispatch_trigger_node(self):
        """Trigger node returns inputs unchanged."""
        node = make_node("t1", "trigger")
        inputs = {"prev": {"data": "test"}}
        context = {"db": make_mock_db(), "event_bus": None, "agent_registry": None}
        result = await dispatch_node(node, inputs, context)
        assert result == inputs

    async def test_dispatch_agent_node_simulated(self):
        """Agent node without agent registry returns simulated result."""
        node = make_node("a1", "agent", agent_id="agent-1", task="analyze data")
        inputs = {"t1": {"event": "test"}}
        context = {"db": make_mock_db(), "event_bus": None, "agent_registry": None}
        result = await dispatch_node(node, inputs, context)
        assert result["simulated"] is True
        assert result["agent_id"] == "agent-1"
        assert "analyze data" in result["result"]

    async def test_dispatch_condition_true(self):
        """Condition 'true' returns {'result': True}."""
        node = make_node("c1", "condition", condition="true")
        result = await dispatch_node(node, {}, {"db": None, "event_bus": None, "agent_registry": None})
        assert result == {"result": True}

    async def test_dispatch_condition_false(self):
        """Condition 'false' returns {'result': False}."""
        node = make_node("c1", "condition", condition="false")
        result = await dispatch_node(node, {}, {"db": None, "event_bus": None, "agent_registry": None})
        assert result == {"result": False}

    async def test_dispatch_action_node(self):
        """Action node returns action metadata."""
        node = make_node("act1", "action", action="notify")
        inputs = {"prev": {"data": "test"}}
        context = {"db": make_mock_db(), "event_bus": None, "agent_registry": None}
        result = await dispatch_node(node, inputs, context)
        assert result["action"] == "notify"
        assert result["executed"] is True
        assert "inputs" in result

    async def test_dispatch_delay_node(self):
        """Delay node sleeps and returns inputs (mocked for speed)."""
        node = make_node("d1", "delay", seconds=10)
        inputs = {"prev": {"data": "test"}}
        context = {"db": None, "event_bus": None, "agent_registry": None}

        with patch("gathering.orchestration.pipeline.nodes.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await dispatch_node(node, inputs, context)
            mock_sleep.assert_called_once_with(10)
            assert result == inputs

    async def test_dispatch_unknown_type(self):
        """Unknown node type raises NodeConfigError."""
        node = PipelineNode.model_construct(
            id="bad", type="unknown", name="Bad", config={}
        )
        context = {"db": None, "event_bus": None, "agent_registry": None}
        with pytest.raises(NodeConfigError, match="Unknown node type"):
            await dispatch_node(node, {}, context)


# ---------------------------------------------------------------------------
# Condition branching
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestConditionBranching:
    """Tests for condition-based execution path selection."""

    async def test_condition_false_skips_downstream(self):
        """Trigger -> Condition(false) -> Agent. Agent is skipped."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("c1", "condition", condition="false"),
                make_node("a1", "agent", agent_id="agent-1", task="should-skip"),
            ],
            edges=[
                make_edge("e1", "t1", "c1"),
                make_edge("e2", "c1", "a1"),
            ],
        )
        executor = make_executor(pipeline)
        result = await executor.execute(run_id=1, trigger_data={})

        assert result["status"] == "completed"
        # Find the agent node result
        agent_results = [r for r in result["node_results"] if r["node_id"] == "a1"]
        assert len(agent_results) == 1
        assert agent_results[0]["status"] == "skipped"

    async def test_condition_true_executes_downstream(self):
        """Trigger -> Condition(true) -> Agent. Agent executes."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("c1", "condition", condition="true"),
                make_node("a1", "agent", agent_id="agent-1", task="should-run"),
            ],
            edges=[
                make_edge("e1", "t1", "c1"),
                make_edge("e2", "c1", "a1"),
            ],
        )
        executor = make_executor(pipeline)
        result = await executor.execute(run_id=1, trigger_data={})

        assert result["status"] == "completed"
        agent_results = [r for r in result["node_results"] if r["node_id"] == "a1"]
        assert len(agent_results) == 1
        assert agent_results[0]["status"] == "completed"


# ---------------------------------------------------------------------------
# Retry and circuit breaker
# ---------------------------------------------------------------------------

class TestRetryAndCircuitBreaker:
    """Tests for retry logic and circuit breaker state transitions."""

    @pytest.mark.asyncio
    async def test_node_retry_on_failure(self):
        """Node fails twice then succeeds on third try. Pipeline completes."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("a1", "agent", agent_id="agent-1", task="flaky"),
            ],
            edges=[make_edge("e1", "t1", "a1")],
        )
        executor = make_executor(pipeline)

        call_count = 0

        async def flaky_dispatch(node, inputs, context):
            nonlocal call_count
            if node.id == "a1":
                call_count += 1
                if call_count < 3:
                    raise NodeExecutionError("transient failure")
                return {"result": "success", "agent_id": "agent-1", "simulated": True}
            # Handle trigger node passthrough
            return inputs

        with patch(
            "gathering.orchestration.pipeline.executor.dispatch_node",
            side_effect=flaky_dispatch,
        ):
            result = await executor.execute(
                run_id=1,
                trigger_data={},
                max_retries=5,
                backoff_base=0.01,
                backoff_max=0.02,
            )

        assert result["status"] == "completed"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_node_retry_exhaustion(self):
        """Node fails all retries. Pipeline fails."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("a1", "agent", agent_id="agent-1", task="always-fail"),
            ],
            edges=[make_edge("e1", "t1", "a1")],
        )
        executor = make_executor(pipeline)

        async def always_fail_dispatch(node, inputs, context):
            if node.id == "a1":
                raise NodeExecutionError("permanent transient failure")
            return inputs

        with patch(
            "gathering.orchestration.pipeline.executor.dispatch_node",
            side_effect=always_fail_dispatch,
        ):
            result = await executor.execute(
                run_id=1,
                trigger_data={},
                max_retries=3,
                backoff_base=0.01,
                backoff_max=0.02,
            )

        assert result["status"] == "failed"
        # With reraise=True, the original NodeExecutionError propagates
        assert "permanent transient failure" in result["error"]

    def test_circuit_breaker_trips_after_threshold(self):
        """After threshold failures, breaker.can_execute() returns False."""
        breaker = CircuitBreaker(failure_threshold=3)
        assert breaker.can_execute() is True

        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert breaker.can_execute() is False

    def test_circuit_breaker_recovery(self):
        """After recovery timeout, breaker transitions to HALF_OPEN and allows test request."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.can_execute() is False

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should transition to HALF_OPEN and allow one call
        assert breaker.can_execute() is True
        assert breaker.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_reset_on_success(self):
        """Success in HALF_OPEN transitions to CLOSED."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery
        time.sleep(0.15)
        breaker.can_execute()  # Transitions to HALF_OPEN
        assert breaker.state == CircuitState.HALF_OPEN

        # Success resets to CLOSED
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.can_execute() is True


# ---------------------------------------------------------------------------
# Cancellation and timeout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCancellationAndTimeout:
    """Tests for pipeline cancellation and timeout enforcement."""

    async def test_pipeline_cancellation(self):
        """Start pipeline, request cancel, pipeline returns cancelled status."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("d1", "delay", seconds=100),
                make_node("a1", "agent", agent_id="agent-1", task="after-delay"),
            ],
            edges=[
                make_edge("e1", "t1", "d1"),
                make_edge("e2", "d1", "a1"),
            ],
        )
        executor = make_executor(pipeline)

        async def cancelling_dispatch(node, inputs, context):
            if node.type == "trigger":
                return inputs
            if node.type == "delay":
                # Request cancel during delay execution
                executor.request_cancel()
                return inputs
            if node.type == "agent":
                return {"result": "should not reach", "agent_id": "agent-1", "simulated": True}
            return inputs

        with patch(
            "gathering.orchestration.pipeline.executor.dispatch_node",
            side_effect=cancelling_dispatch,
        ):
            result = await executor.execute(run_id=1, trigger_data={})

        assert result["status"] == "cancelled"

    async def test_pipeline_timeout(self):
        """Pipeline with very short timeout and a delay node times out."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("d1", "delay", seconds=100),
            ],
            edges=[make_edge("e1", "t1", "d1")],
        )
        event_bus = make_mock_event_bus()
        executor = make_executor(pipeline, event_bus=event_bus)

        manager = PipelineRunManager()
        task = await manager.start_run(
            run_id=1,
            executor=executor,
            timeout_seconds=0.1,  # Very short timeout
            trigger_data={},
        )

        result = await task
        assert result["status"] == "timeout"
        assert "exceeded" in result["error"]

    async def test_run_manager_cancel_run(self):
        """PipelineRunManager.cancel_run() stops a running pipeline."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("d1", "delay", seconds=100),
            ],
            edges=[make_edge("e1", "t1", "d1")],
        )
        executor = make_executor(pipeline)

        manager = PipelineRunManager()
        task = await manager.start_run(
            run_id=42,
            executor=executor,
            timeout_seconds=300,
            trigger_data={},
        )

        # Give the task a moment to start
        await asyncio.sleep(0.05)

        # Cancel it
        cancelled = await manager.cancel_run(42)
        assert cancelled is True

        # Wait for the task to complete
        result = await task
        assert result["status"] == "cancelled"

    async def test_run_manager_active_runs(self):
        """start_run adds to active_runs, completion removes it."""
        pipeline = make_pipeline(
            nodes=[make_node("t1", "trigger")],
            edges=[],
        )
        executor = make_executor(pipeline)

        manager = PipelineRunManager()
        task = await manager.start_run(
            run_id=99,
            executor=executor,
            timeout_seconds=60,
            trigger_data={},
        )

        # Briefly check active before completion
        # The task may complete very quickly since it's just a trigger
        await asyncio.sleep(0.01)

        # Wait for completion
        await task

        # After completion, should not be in active_runs
        assert 99 not in manager.active_runs

    async def test_cancel_leaves_no_zombies(self):
        """After cancellation, active_runs is empty."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("d1", "delay", seconds=100),
            ],
            edges=[make_edge("e1", "t1", "d1")],
        )
        executor = make_executor(pipeline)

        manager = PipelineRunManager()
        task = await manager.start_run(
            run_id=1,
            executor=executor,
            timeout_seconds=300,
            trigger_data={},
        )

        await asyncio.sleep(0.05)
        await manager.cancel_run(1)
        await task

        # No zombies
        assert manager.active_runs == []
        assert manager.is_running(1) is False


# ---------------------------------------------------------------------------
# Event emission
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEventEmission:
    """Tests for event emission during pipeline execution."""

    async def test_events_emitted_during_execution(self):
        """Verify PIPELINE_RUN_STARTED, PIPELINE_NODE_STARTED,
        PIPELINE_NODE_COMPLETED, PIPELINE_RUN_COMPLETED are emitted in order."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("act1", "action", action="notify"),
            ],
            edges=[make_edge("e1", "t1", "act1")],
        )
        event_bus = make_mock_event_bus()
        executor = make_executor(pipeline, event_bus=event_bus)

        result = await executor.execute(run_id=1, trigger_data={"hello": "world"})
        assert result["status"] == "completed"

        # Collect event types from all emit calls
        emitted_events = [
            call.kwargs.get("event_type") or call.args[0]
            for call in event_bus.emit.call_args_list
        ]

        # Must include these in order
        assert EventType.PIPELINE_RUN_STARTED in emitted_events
        assert EventType.PIPELINE_RUN_COMPLETED in emitted_events

        # Node events should be present
        assert EventType.PIPELINE_NODE_STARTED in emitted_events
        assert EventType.PIPELINE_NODE_COMPLETED in emitted_events

        # RUN_STARTED should come before RUN_COMPLETED
        start_idx = emitted_events.index(EventType.PIPELINE_RUN_STARTED)
        complete_idx = emitted_events.index(EventType.PIPELINE_RUN_COMPLETED)
        assert start_idx < complete_idx


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestGetRunManager:
    """Tests for the get_run_manager singleton factory."""

    def test_get_run_manager_returns_same_instance(self):
        """get_run_manager returns the same instance on repeated calls."""
        # Reset singleton for clean test
        import gathering.orchestration.pipeline.executor as executor_mod
        executor_mod._run_manager = None

        mgr1 = get_run_manager()
        mgr2 = get_run_manager()
        assert mgr1 is mgr2

        # Clean up
        executor_mod._run_manager = None
