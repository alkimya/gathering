"""
Pipeline DAG validation using graphlib.TopologicalSorter.

Validates pipeline structure before execution:
- Rejects cycles (CycleError)
- Rejects dangling edge references
- Rejects invalid node types (handled by Pydantic, but double-checked for raw dict input)
- Warns about orphan nodes (no edges, not trigger type)
- Validates node-type-specific config requirements
"""

import graphlib
import logging
from typing import Any

from pydantic import ValidationError

from gathering.orchestration.pipeline.models import (
    PipelineDefinition,
    PipelineEdge,
    PipelineNode,
)

logger = logging.getLogger(__name__)

VALID_NODE_TYPES = {"trigger", "agent", "condition", "action", "parallel", "delay"}


def validate_pipeline_dag(definition: PipelineDefinition) -> list[str]:
    """Validate a pipeline definition as a valid DAG.

    Returns a list of error strings. An empty list means the pipeline is valid.

    Checks performed:
    1. At least one node exists
    2. All node types are valid
    3. All edge endpoints reference existing node IDs
    4. Orphan nodes (no edges, not trigger) generate warnings (logged, not errors)
    5. No cycles (via graphlib.TopologicalSorter / CycleError)
    6. Node-type-specific config validation (agent needs agent_id, condition needs condition)
    """
    errors: list[str] = []

    # 1. Check at least one node
    if not definition.nodes:
        errors.append("Pipeline must have at least one node")
        return errors

    node_map = definition.node_map
    node_ids = set(node_map.keys())

    # 2. Check all node types are valid (Pydantic handles this for typed input,
    #    but raw dict input may bypass it)
    for node in definition.nodes:
        if node.type not in VALID_NODE_TYPES:
            errors.append(
                f"Node '{node.id}' has invalid type: '{node.type}'. "
                f"Valid types: {sorted(VALID_NODE_TYPES)}"
            )

    # 3. Check all edge endpoints reference existing node IDs
    for edge in definition.edges:
        if edge.from_node not in node_ids:
            errors.append(
                f"Edge '{edge.id}' references unknown source node: '{edge.from_node}'"
            )
        if edge.to_node not in node_ids:
            errors.append(
                f"Edge '{edge.id}' references unknown target node: '{edge.to_node}'"
            )

    # If there are already structural errors, skip cycle detection
    if errors:
        return errors

    # 4. Check for orphan nodes (warn, don't error)
    connected_nodes: set[str] = set()
    for edge in definition.edges:
        connected_nodes.add(edge.from_node)
        connected_nodes.add(edge.to_node)

    for node in definition.nodes:
        if node.id not in connected_nodes and node.type != "trigger":
            logger.warning(
                "Orphan node '%s' (type=%s) has no edges and is not a trigger node",
                node.id,
                node.type,
            )

    # 5. Build predecessor graph and check for cycles
    graph: dict[str, set[str]] = {node.id: set() for node in definition.nodes}
    for edge in definition.edges:
        graph[edge.to_node].add(edge.from_node)

    try:
        ts = graphlib.TopologicalSorter(graph)
        list(ts.static_order())  # Forces full traversal; raises CycleError if cycle
    except graphlib.CycleError as e:
        cycle_info = e.args[1] if len(e.args) > 1 else "unknown"
        errors.append(f"Pipeline contains a cycle: {cycle_info}")

    # 6. Validate node-type-specific config
    for node in definition.nodes:
        config = node.config
        if node.type == "agent":
            if "agent_id" not in config:
                errors.append(
                    f"Agent node '{node.id}' is missing required config key 'agent_id'"
                )
            if "task" not in config:
                errors.append(
                    f"Agent node '{node.id}' is missing required config key 'task'"
                )
        elif node.type == "condition":
            if "condition" not in config:
                errors.append(
                    f"Condition node '{node.id}' is missing required config key 'condition'"
                )

    return errors


def get_execution_order(definition: PipelineDefinition) -> list[str]:
    """Return node IDs in topological execution order.

    Raises ValueError if the graph contains cycles.
    Used by the pipeline executor (Plan 02-02) to determine node execution sequence.
    """
    if not definition.nodes:
        return []

    # Build predecessor graph
    graph: dict[str, set[str]] = {node.id: set() for node in definition.nodes}
    for edge in definition.edges:
        graph[edge.to_node].add(edge.from_node)

    try:
        ts = graphlib.TopologicalSorter(graph)
        return list(ts.static_order())
    except graphlib.CycleError as e:
        cycle_info = e.args[1] if len(e.args) > 1 else "unknown"
        raise ValueError(f"Pipeline contains a cycle: {cycle_info}") from e


def parse_pipeline_definition(
    nodes_json: list[dict[str, Any]],
    edges_json: list[dict[str, Any]],
) -> PipelineDefinition:
    """Parse raw JSONB lists into a validated PipelineDefinition.

    Args:
        nodes_json: List of node dicts from circle.pipelines.nodes JSONB column.
        edges_json: List of edge dicts from circle.pipelines.edges JSONB column.

    Returns:
        Validated PipelineDefinition.

    Raises:
        ValueError: If parsing or validation fails, with details about the errors.
    """
    try:
        nodes = [PipelineNode(**n) for n in nodes_json]
    except (ValidationError, TypeError) as e:
        raise ValueError(f"Invalid node data: {e}") from e

    try:
        edges = [PipelineEdge(**e) for e in edges_json]
    except (ValidationError, TypeError) as e:
        raise ValueError(f"Invalid edge data: {e}") from e

    return PipelineDefinition(nodes=nodes, edges=edges)
