"""
Node type dispatchers for pipeline execution.

Each node type has a handler that receives the node definition,
inputs from predecessor nodes, and an execution context dict.
"""

import asyncio
import logging
from typing import Any

from gathering.orchestration.pipeline.models import PipelineNode

logger = logging.getLogger(__name__)


class NodeExecutionError(Exception):
    """Retryable error during node execution.

    Raised when a node handler fails in a way that may succeed on retry
    (e.g., transient network error, temporary service unavailability).
    """


class NodeConfigError(Exception):
    """Non-retryable error due to invalid node configuration.

    Raised when a node's config is invalid or missing required fields.
    Should NOT trigger retry -- the config won't fix itself.
    """


async def dispatch_node(
    node: PipelineNode,
    inputs: dict[str, Any],
    context: dict,
) -> dict:
    """Dispatch a pipeline node to its type-specific handler.

    Args:
        node: The pipeline node to execute.
        inputs: Dict of {predecessor_node_id: predecessor_output} from upstream nodes.
        context: Execution context containing:
            - db: DatabaseService instance
            - event_bus: EventBus instance (optional)
            - agent_registry: AgentRegistry or similar (optional)

    Returns:
        Dict with node output data.

    Raises:
        NodeExecutionError: On retryable failures.
        NodeConfigError: On configuration errors (not retryable).
    """
    handler = _NODE_HANDLERS.get(node.type)
    if handler is None:
        raise NodeConfigError(
            f"Unknown node type '{node.type}' for node '{node.id}'"
        )
    return await handler(node, inputs, context)


async def _handle_trigger(
    node: PipelineNode,
    inputs: dict[str, Any],
    context: dict,
) -> dict:
    """Trigger node: passthrough. Returns inputs unchanged."""
    return inputs


async def _handle_agent(
    node: PipelineNode,
    inputs: dict[str, Any],
    context: dict,
) -> dict:
    """Agent node: dispatch to agent for LLM execution.

    If agent_registry is available in context, looks up the agent and
    calls process_message. Otherwise, returns a simulated result for
    graceful degradation.
    """
    agent_id = node.config.get("agent_id")
    task = node.config.get("task", "")

    if not agent_id:
        raise NodeConfigError(
            f"Agent node '{node.id}' missing 'agent_id' in config"
        )

    agent_registry = context.get("agent_registry")
    if agent_registry is not None:
        try:
            # Try integer lookup first, fall back to string
            try:
                agent = agent_registry.get(int(agent_id))
            except (ValueError, TypeError):
                agent = agent_registry.get(agent_id)

            if agent is not None and hasattr(agent, "process_message"):
                # Build prompt from task and inputs
                prompt = task
                if inputs:
                    input_summary = "; ".join(
                        f"{k}: {v}" for k, v in inputs.items()
                    )
                    prompt = f"{task}\n\nContext from previous nodes:\n{input_summary}"

                process_fn = agent.process_message
                if callable(process_fn):
                    result_text = await process_fn(prompt)
                    return {
                        "result": result_text,
                        "agent_id": agent_id,
                        "simulated": False,
                    }
        except Exception as e:
            raise NodeExecutionError(
                f"Agent node '{node.id}' failed: {e}"
            ) from e

    # Graceful degradation: no registry or agent not found
    logger.info(
        "Agent node '%s': no agent_registry or agent '%s' not found, returning simulated result",
        node.id,
        agent_id,
    )
    return {
        "result": f"Agent {agent_id} task: {task}",
        "agent_id": agent_id,
        "simulated": True,
    }


async def _handle_condition(
    node: PipelineNode,
    inputs: dict[str, Any],
    context: dict,
) -> dict:
    """Condition node: evaluate condition expression against inputs.

    Supports safe evaluation without eval():
    - "true" / "false" literals
    - "input.<key>" checks if a specific input key is truthy
    - Any other string is treated as a key path into predecessor outputs
    """
    condition_expr = node.config.get("condition", "true")

    # Literal booleans
    if condition_expr.lower() == "true":
        return {"result": True}
    if condition_expr.lower() == "false":
        return {"result": False}

    # Input reference: "input.result" checks inputs[predecessor_id]["result"]
    if condition_expr.startswith("input."):
        field_name = condition_expr[len("input."):]
        # Check across all predecessor outputs
        for pred_id, pred_output in inputs.items():
            if isinstance(pred_output, dict) and field_name in pred_output:
                value = pred_output[field_name]
                return {"result": bool(value)}
        # Field not found in any predecessor -- treat as falsy
        return {"result": False}

    # Check if condition matches a predecessor node ID key
    if condition_expr in inputs:
        return {"result": bool(inputs[condition_expr])}

    # Default: treat non-empty string as truthy
    return {"result": bool(condition_expr)}


async def _handle_action(
    node: PipelineNode,
    inputs: dict[str, Any],
    context: dict,
) -> dict:
    """Action node: log and return action metadata.

    Real action dispatch will be extended in Phase 3.
    """
    action_type = node.config.get("action", "unknown")

    # Summarize inputs (truncate large values)
    summarized_inputs = {}
    for k, v in inputs.items():
        s = str(v)
        summarized_inputs[k] = s[:200] if len(s) > 200 else s

    logger.info(
        "Action node '%s': executing action '%s'",
        node.id,
        action_type,
    )

    return {
        "action": action_type,
        "executed": True,
        "inputs": summarized_inputs,
    }


async def _handle_parallel(
    node: PipelineNode,
    inputs: dict[str, Any],
    context: dict,
) -> dict:
    """Parallel node: passthrough (fan-out handled by executor topology)."""
    return inputs


async def _handle_delay(
    node: PipelineNode,
    inputs: dict[str, Any],
    context: dict,
) -> dict:
    """Delay node: wait for configured seconds, then pass inputs through."""
    seconds = node.config.get("seconds", 0)
    if seconds > 0:
        await asyncio.sleep(seconds)
    return inputs


# Handler dispatch table
_NODE_HANDLERS = {
    "trigger": _handle_trigger,
    "agent": _handle_agent,
    "condition": _handle_condition,
    "action": _handle_action,
    "parallel": _handle_parallel,
    "delay": _handle_delay,
}
