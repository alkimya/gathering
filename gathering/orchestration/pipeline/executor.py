"""
Pipeline execution engine.

Traverses pipeline DAGs in topological order, dispatching each node
to its type-specific handler, passing outputs between nodes,
retrying failures with exponential backoff via tenacity, and tripping
circuit breakers after retry exhaustion.
"""

import asyncio
import json
import logging
import time
from typing import Any, Optional

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from gathering.orchestration.events import EventBus, EventType
from gathering.orchestration.pipeline.circuit_breaker import CircuitBreaker
from gathering.orchestration.pipeline.models import (
    NodeExecutionResult,
    PipelineDefinition,
)
from gathering.orchestration.pipeline.nodes import (
    NodeExecutionError,
    dispatch_node,
)
from gathering.orchestration.pipeline.validator import (
    get_execution_order,
    validate_pipeline_dag,
)

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """Core pipeline execution engine.

    Executes a pipeline by traversing its DAG in topological order,
    dispatching each node to the appropriate handler, collecting outputs,
    and managing retries and circuit breakers.
    """

    def __init__(
        self,
        pipeline_id: int,
        definition: PipelineDefinition,
        db: Any,
        event_bus: Optional[EventBus] = None,
        agent_registry: Optional[Any] = None,
    ):
        self.pipeline_id = pipeline_id
        self.definition = definition
        self.db = db
        self.event_bus = event_bus
        self.agent_registry = agent_registry

        self._cancel_requested = False
        self._node_outputs: dict[str, Any] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

        # Initialize circuit breakers per node
        for node in definition.nodes:
            threshold = node.config.get("failure_threshold", 5)
            self._circuit_breakers[node.id] = CircuitBreaker(
                failure_threshold=threshold
            )

    def request_cancel(self) -> None:
        """Request cancellation of the running pipeline."""
        self._cancel_requested = True

    async def execute(
        self,
        run_id: int,
        trigger_data: Optional[dict] = None,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_max: float = 60.0,
    ) -> dict:
        """Execute the pipeline DAG.

        Args:
            run_id: The pipeline run ID for tracking.
            trigger_data: Initial data passed to trigger nodes.
            max_retries: Maximum retry attempts per node.
            backoff_base: Base multiplier for exponential backoff.
            backoff_max: Maximum backoff wait time in seconds.

        Returns:
            Dict with status, outputs, and node_results.
        """
        node_results: list[dict] = []

        try:
            # 1. Validate pipeline
            errors = validate_pipeline_dag(self.definition)
            if errors:
                error_msg = "Validation failed: " + "; ".join(errors)
                await self._emit_event(
                    EventType.PIPELINE_RUN_FAILED,
                    {"pipeline_id": self.pipeline_id, "run_id": run_id, "error": error_msg},
                )
                return {"status": "failed", "error": error_msg}

            # 2. Emit run started
            await self._emit_event(
                EventType.PIPELINE_RUN_STARTED,
                {"pipeline_id": self.pipeline_id, "run_id": run_id},
            )

            # 3. Get execution order
            execution_order = get_execution_order(self.definition)
            node_map = self.definition.node_map

            # 4. Build predecessor map from edges
            predecessors: dict[str, set[str]] = {
                node.id: set() for node in self.definition.nodes
            }
            # Also build successor map for condition skip propagation
            successors: dict[str, set[str]] = {
                node.id: set() for node in self.definition.nodes
            }
            for edge in self.definition.edges:
                predecessors[edge.to_node].add(edge.from_node)
                successors[edge.from_node].add(edge.to_node)

            # 5. Set trigger node outputs
            trigger_output = trigger_data or {}
            for node in self.definition.nodes:
                if node.type == "trigger":
                    self._node_outputs[node.id] = trigger_output

            # 6. Track skipped nodes
            skipped_nodes: set[str] = set()

            # Build execution context
            context = {
                "db": self.db,
                "event_bus": self.event_bus,
                "agent_registry": self.agent_registry,
            }

            # 7. Loop through nodes in topological order
            for node_id in execution_order:
                # 7a. Check cancellation
                if self._cancel_requested:
                    await self._emit_event(
                        EventType.PIPELINE_RUN_CANCELLED,
                        {"pipeline_id": self.pipeline_id, "run_id": run_id},
                    )
                    return {
                        "status": "cancelled",
                        "node_results": node_results,
                        "outputs": self._node_outputs,
                    }

                node = node_map.get(node_id)
                if node is None:
                    continue

                # 7b. Check if node should be skipped
                # A node is skipped if: it was already marked by a false condition's
                # downstream propagation, OR all its predecessors are skipped.
                node_preds = predecessors.get(node_id, set())
                should_skip = (
                    node_id in skipped_nodes
                    or (node_preds and all(p in skipped_nodes for p in node_preds))
                )
                if should_skip:
                    skipped_nodes.add(node_id)
                    await self._emit_event(
                        EventType.PIPELINE_NODE_SKIPPED,
                        {"pipeline_id": self.pipeline_id, "run_id": run_id, "node_id": node_id},
                    )
                    result = NodeExecutionResult(
                        node_id=node_id,
                        status="skipped",
                    )
                    node_results.append(result.model_dump())
                    await self._persist_node_run(run_id, result)
                    continue

                # Skip trigger nodes that already have output set
                if node.type == "trigger" and node_id in self._node_outputs:
                    result = NodeExecutionResult(
                        node_id=node_id,
                        status="completed",
                        output=self._node_outputs[node_id],
                    )
                    node_results.append(result.model_dump())
                    await self._persist_node_run(run_id, result)
                    continue

                # 7c. Emit node started
                await self._emit_event(
                    EventType.PIPELINE_NODE_STARTED,
                    {"pipeline_id": self.pipeline_id, "run_id": run_id, "node_id": node_id},
                )

                # 7d. Gather inputs from predecessors
                inputs: dict[str, Any] = {}
                for pred_id in node_preds:
                    if pred_id not in skipped_nodes and pred_id in self._node_outputs:
                        inputs[pred_id] = self._node_outputs[pred_id]

                # 7e. Check circuit breaker
                breaker = self._circuit_breakers.get(node_id)
                if breaker and not breaker.can_execute():
                    error_msg = f"Circuit breaker OPEN for node '{node_id}'"
                    await self._emit_event(
                        EventType.PIPELINE_NODE_FAILED,
                        {
                            "pipeline_id": self.pipeline_id,
                            "run_id": run_id,
                            "node_id": node_id,
                            "error": error_msg,
                        },
                    )
                    result = NodeExecutionResult(
                        node_id=node_id,
                        status="failed",
                        error=error_msg,
                    )
                    node_results.append(result.model_dump())
                    await self._persist_node_run(run_id, result)

                    # If this is a critical node (not condition), fail the pipeline
                    if node.type != "condition":
                        await self._emit_event(
                            EventType.PIPELINE_RUN_FAILED,
                            {
                                "pipeline_id": self.pipeline_id,
                                "run_id": run_id,
                                "error": error_msg,
                            },
                        )
                        return {
                            "status": "failed",
                            "error": error_msg,
                            "node_results": node_results,
                            "outputs": self._node_outputs,
                        }
                    continue

                # 7f. Execute with retry
                start_time = time.monotonic()
                retry_count = 0

                try:
                    # Build retry-wrapped function
                    @retry(
                        stop=stop_after_attempt(max_retries),
                        wait=wait_exponential(
                            multiplier=backoff_base, max=backoff_max
                        ),
                        retry=retry_if_exception_type(NodeExecutionError),
                        before_sleep=lambda rs: self._on_retry(
                            run_id, node_id, rs.attempt_number
                        ),
                        reraise=True,
                    )
                    async def _run_node():
                        return await dispatch_node(node, inputs, context)

                    output = await _run_node()
                    duration_ms = int((time.monotonic() - start_time) * 1000)

                    # 7g. Success
                    if breaker:
                        breaker.record_success()
                    self._node_outputs[node_id] = output

                    await self._emit_event(
                        EventType.PIPELINE_NODE_COMPLETED,
                        {
                            "pipeline_id": self.pipeline_id,
                            "run_id": run_id,
                            "node_id": node_id,
                            "duration_ms": duration_ms,
                        },
                    )

                    result = NodeExecutionResult(
                        node_id=node_id,
                        status="completed",
                        output=output,
                        duration_ms=duration_ms,
                        retry_count=retry_count,
                    )
                    node_results.append(result.model_dump())
                    await self._persist_node_run(run_id, result)

                    # 7i. For condition nodes: if result is False, skip downstream
                    if node.type == "condition" and isinstance(output, dict):
                        condition_result = output.get("result", True)
                        if not condition_result:
                            # Find nodes reachable only through this condition
                            self._mark_downstream_skipped(
                                node_id, predecessors, successors, skipped_nodes
                            )

                except RetryError as e:
                    # 7h. Failure after retry exhaustion
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    original_error = str(e.last_attempt.exception()) if e.last_attempt.exception() else str(e)

                    if breaker:
                        breaker.record_failure()

                    await self._emit_event(
                        EventType.PIPELINE_NODE_FAILED,
                        {
                            "pipeline_id": self.pipeline_id,
                            "run_id": run_id,
                            "node_id": node_id,
                            "error": original_error,
                        },
                    )

                    result = NodeExecutionResult(
                        node_id=node_id,
                        status="failed",
                        error=original_error,
                        duration_ms=duration_ms,
                        retry_count=max_retries,
                    )
                    node_results.append(result.model_dump())
                    await self._persist_node_run(run_id, result)

                    # If node is critical (non-condition), fail the pipeline
                    if node.type != "condition":
                        await self._emit_event(
                            EventType.PIPELINE_RUN_FAILED,
                            {
                                "pipeline_id": self.pipeline_id,
                                "run_id": run_id,
                                "error": f"Node '{node_id}' failed after {max_retries} retries: {original_error}",
                            },
                        )
                        return {
                            "status": "failed",
                            "error": f"Node '{node_id}' failed after {max_retries} retries: {original_error}",
                            "node_results": node_results,
                            "outputs": self._node_outputs,
                        }

                except Exception as e:
                    # Non-retryable error (e.g., NodeConfigError)
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    error_msg = str(e)

                    await self._emit_event(
                        EventType.PIPELINE_NODE_FAILED,
                        {
                            "pipeline_id": self.pipeline_id,
                            "run_id": run_id,
                            "node_id": node_id,
                            "error": error_msg,
                        },
                    )

                    result = NodeExecutionResult(
                        node_id=node_id,
                        status="failed",
                        error=error_msg,
                        duration_ms=duration_ms,
                    )
                    node_results.append(result.model_dump())
                    await self._persist_node_run(run_id, result)

                    if node.type != "condition":
                        await self._emit_event(
                            EventType.PIPELINE_RUN_FAILED,
                            {
                                "pipeline_id": self.pipeline_id,
                                "run_id": run_id,
                                "error": error_msg,
                            },
                        )
                        return {
                            "status": "failed",
                            "error": error_msg,
                            "node_results": node_results,
                            "outputs": self._node_outputs,
                        }

            # 8. All nodes completed successfully
            await self._emit_event(
                EventType.PIPELINE_RUN_COMPLETED,
                {"pipeline_id": self.pipeline_id, "run_id": run_id},
            )
            return {
                "status": "completed",
                "outputs": self._node_outputs,
                "node_results": node_results,
            }

        except Exception as e:
            # Unexpected error during execution
            logger.exception("Unexpected error executing pipeline %s", self.pipeline_id)
            await self._emit_event(
                EventType.PIPELINE_RUN_FAILED,
                {
                    "pipeline_id": self.pipeline_id,
                    "run_id": run_id,
                    "error": str(e),
                },
            )
            return {
                "status": "failed",
                "error": str(e),
                "node_results": node_results,
                "outputs": self._node_outputs,
            }

    def _mark_downstream_skipped(
        self,
        condition_node_id: str,
        predecessors: dict[str, set[str]],
        successors: dict[str, set[str]],
        skipped_nodes: set[str],
    ) -> None:
        """Mark downstream nodes of a false condition for skipping.

        A downstream node is skipped only if ALL its predecessors
        are either the false condition node or already in skipped_nodes.
        The false condition node itself is treated as a "skip source"
        but is NOT added to skipped_nodes (it executed successfully).
        """
        # Include the condition node in the set of "skip sources" for checking
        skip_sources = skipped_nodes | {condition_node_id}
        to_check = list(successors.get(condition_node_id, set()))
        while to_check:
            candidate = to_check.pop(0)
            if candidate in skipped_nodes:
                continue
            # Skip if all predecessors are skip sources
            candidate_preds = predecessors.get(candidate, set())
            if candidate_preds and all(
                p in skip_sources for p in candidate_preds
            ):
                skipped_nodes.add(candidate)
                skip_sources.add(candidate)
                # Also check this node's successors
                to_check.extend(successors.get(candidate, set()))

    def _on_retry(self, run_id: int, node_id: str, attempt: int) -> None:
        """Callback before each retry sleep. Emits retrying event."""
        logger.info(
            "Retrying node '%s' (attempt %d) in pipeline run %d",
            node_id,
            attempt,
            run_id,
        )
        # Fire-and-forget event emission (sync context in before_sleep)
        # The event will be emitted asynchronously by the event bus if available
        if self.event_bus:
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(
                        self._emit_event(
                            EventType.PIPELINE_NODE_RETRYING,
                            {
                                "pipeline_id": self.pipeline_id,
                                "run_id": run_id,
                                "node_id": node_id,
                                "attempt": attempt,
                            },
                        )
                    )
            except Exception:
                pass  # Never fail the pipeline due to event emission

    async def _persist_node_run(self, run_id: int, result: NodeExecutionResult) -> None:
        """Persist a node execution result to the database."""
        try:
            self.db.execute(
                """
                INSERT INTO circle.pipeline_node_runs
                    (run_id, node_id, status, output, error_message, duration_ms, retry_count)
                VALUES
                    (%(run_id)s, %(node_id)s, %(status)s, %(output)s::jsonb,
                     %(error)s, %(duration_ms)s, %(retry_count)s)
                """,
                {
                    "run_id": run_id,
                    "node_id": result.node_id,
                    "status": result.status,
                    "output": json.dumps(result.output) if result.output else None,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                    "retry_count": result.retry_count,
                },
            )
        except Exception as e:
            # Never fail the pipeline due to persistence errors
            logger.warning(
                "Failed to persist node run for %s: %s", result.node_id, e
            )

    async def _emit_event(self, event_type: EventType, data: dict) -> None:
        """Emit a pipeline event if event_bus is available.

        Never raises -- event emission failures are logged and swallowed
        to avoid disrupting pipeline execution.
        """
        if not self.event_bus:
            return
        try:
            await self.event_bus.emit(
                event_type=event_type,
                data=data,
                source_agent_id=None,
            )
        except Exception as e:
            logger.warning(
                "Failed to emit event %s: %s", event_type.value, e
            )


class PipelineRunManager:
    """Manages active pipeline runs with cancellation and timeout enforcement.

    Tracks running pipelines so they can be cancelled by run_id.
    Enforces per-pipeline timeout using asyncio.timeout.
    Cleans up resources on cancellation/timeout.
    """

    def __init__(self) -> None:
        self._running: dict[int, asyncio.Task] = {}  # run_id -> asyncio.Task
        self._executors: dict[int, PipelineExecutor] = {}  # run_id -> executor

    @property
    def active_runs(self) -> list[int]:
        """Return IDs of currently running pipelines."""
        return [rid for rid, task in self._running.items() if not task.done()]

    async def start_run(
        self,
        run_id: int,
        executor: PipelineExecutor,
        timeout_seconds: int = 3600,
        trigger_data: Optional[dict] = None,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_max: float = 60.0,
    ) -> asyncio.Task:
        """Start a pipeline run with timeout enforcement."""
        self._executors[run_id] = executor

        async def _run_with_timeout():
            try:
                async with asyncio.timeout(timeout_seconds):
                    result = await executor.execute(
                        run_id=run_id,
                        trigger_data=trigger_data,
                        max_retries=max_retries,
                        backoff_base=backoff_base,
                        backoff_max=backoff_max,
                    )
                    return result
            except TimeoutError:
                executor.request_cancel()  # Cooperative cancel
                result = {
                    "status": "timeout",
                    "error": f"Pipeline exceeded {timeout_seconds}s timeout",
                }
                # Emit timeout event
                await executor._emit_event(
                    EventType.PIPELINE_RUN_TIMEOUT,
                    {
                        "run_id": run_id,
                        "pipeline_id": executor.pipeline_id,
                        "timeout_seconds": timeout_seconds,
                    },
                )
                return result
            except asyncio.CancelledError:
                executor.request_cancel()
                return {"status": "cancelled", "error": "Pipeline run was cancelled"}
            finally:
                self._running.pop(run_id, None)
                self._executors.pop(run_id, None)

        task = asyncio.create_task(_run_with_timeout())
        self._running[run_id] = task
        return task

    async def cancel_run(self, run_id: int) -> bool:
        """Cancel a running pipeline. Returns True if cancellation was initiated."""
        executor = self._executors.get(run_id)
        if executor:
            executor.request_cancel()  # Cooperative first

        task = self._running.get(run_id)
        if task and not task.done():
            task.cancel()  # Force cancellation
            return True
        return False

    async def cancel_all(self) -> int:
        """Cancel all running pipelines. Returns count of cancelled runs."""
        cancelled = 0
        for run_id in list(self._running.keys()):
            if await self.cancel_run(run_id):
                cancelled += 1
        return cancelled

    def is_running(self, run_id: int) -> bool:
        """Check if a pipeline run is still active."""
        task = self._running.get(run_id)
        return task is not None and not task.done()


_run_manager: Optional[PipelineRunManager] = None


def get_run_manager() -> PipelineRunManager:
    """Get or create the singleton PipelineRunManager."""
    global _run_manager
    if _run_manager is None:
        _run_manager = PipelineRunManager()
    return _run_manager
