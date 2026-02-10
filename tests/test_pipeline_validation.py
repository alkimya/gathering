"""
Comprehensive pipeline DAG validation tests.

Tests cover: cycle detection, valid DAG acceptance, invalid node types,
dangling edges, missing agent config, execution order, JSONB parsing,
and PipelineEdge alias handling.
"""

import pytest

from gathering.orchestration.pipeline.models import (
    PipelineDefinition,
    PipelineEdge,
    PipelineNode,
)
from gathering.orchestration.pipeline.validator import (
    get_execution_order,
    parse_pipeline_definition,
    validate_pipeline_dag,
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
    """Create a PipelineEdge using the 'from'/'to' alias."""
    return PipelineEdge(id=edge_id, **{"from": from_node, "to": to_node})


def make_pipeline(nodes: list[PipelineNode], edges: list[PipelineEdge]) -> PipelineDefinition:
    """Create a PipelineDefinition from nodes and edges."""
    return PipelineDefinition(nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# Valid pipelines
# ---------------------------------------------------------------------------

class TestValidPipelines:
    """Tests that valid pipeline structures pass validation."""

    def test_valid_linear_pipeline(self):
        """3-node linear pipeline: trigger -> agent -> action, no errors."""
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
        errors = validate_pipeline_dag(pipeline)
        assert errors == []

    def test_valid_branching_pipeline(self):
        """Trigger -> 2 parallel agents -> merge action, no errors."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("a1", "agent", agent_id="agent-1", task="task-1"),
                make_node("a2", "agent", agent_id="agent-2", task="task-2"),
                make_node("merge", "action", action="merge"),
            ],
            edges=[
                make_edge("e1", "t1", "a1"),
                make_edge("e2", "t1", "a2"),
                make_edge("e3", "a1", "merge"),
                make_edge("e4", "a2", "merge"),
            ],
        )
        errors = validate_pipeline_dag(pipeline)
        assert errors == []


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

class TestCycleDetection:
    """Tests that cycles are rejected."""

    def test_cycle_detection_simple(self):
        """A -> B -> A: simple cycle detected."""
        pipeline = make_pipeline(
            nodes=[
                make_node("A", "action", action="a"),
                make_node("B", "action", action="b"),
            ],
            edges=[
                make_edge("e1", "A", "B"),
                make_edge("e2", "B", "A"),
            ],
        )
        errors = validate_pipeline_dag(pipeline)
        assert len(errors) > 0
        assert any("cycle" in e.lower() for e in errors)

    def test_cycle_detection_complex(self):
        """A -> B -> C -> D -> B: cycle deeper in graph."""
        pipeline = make_pipeline(
            nodes=[
                make_node("A", "trigger"),
                make_node("B", "action", action="b"),
                make_node("C", "action", action="c"),
                make_node("D", "action", action="d"),
            ],
            edges=[
                make_edge("e1", "A", "B"),
                make_edge("e2", "B", "C"),
                make_edge("e3", "C", "D"),
                make_edge("e4", "D", "B"),
            ],
        )
        errors = validate_pipeline_dag(pipeline)
        assert len(errors) > 0
        assert any("cycle" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Invalid structures
# ---------------------------------------------------------------------------

class TestInvalidStructures:
    """Tests that invalid pipeline structures produce errors."""

    def test_empty_pipeline_rejected(self):
        """Pipeline with no nodes produces an error."""
        pipeline = make_pipeline(nodes=[], edges=[])
        errors = validate_pipeline_dag(pipeline)
        assert len(errors) > 0
        assert any("at least one node" in e.lower() for e in errors)

    def test_invalid_node_type(self):
        """Node with type 'invalid' is rejected."""
        # PipelineNode uses Literal type, so we must bypass Pydantic validation
        # by constructing a definition with a monkey-patched node
        pipeline = make_pipeline(
            nodes=[make_node("t1", "trigger")],
            edges=[],
        )
        # Manually inject an invalid-type node
        pipeline.nodes.append(
            PipelineNode.model_construct(
                id="bad", type="invalid", name="Bad Node", config={}
            )
        )
        errors = validate_pipeline_dag(pipeline)
        assert len(errors) > 0
        assert any("invalid type" in e.lower() for e in errors)

    def test_dangling_edge_source(self):
        """Edge from non-existent node produces error."""
        pipeline = make_pipeline(
            nodes=[make_node("a1", "action", action="a")],
            edges=[make_edge("e1", "ghost", "a1")],
        )
        errors = validate_pipeline_dag(pipeline)
        assert len(errors) > 0
        assert any("unknown source" in e.lower() for e in errors)

    def test_dangling_edge_target(self):
        """Edge to non-existent node produces error."""
        pipeline = make_pipeline(
            nodes=[make_node("a1", "action", action="a")],
            edges=[make_edge("e1", "a1", "ghost")],
        )
        errors = validate_pipeline_dag(pipeline)
        assert len(errors) > 0
        assert any("unknown target" in e.lower() for e in errors)

    def test_agent_node_missing_config(self):
        """Agent node without agent_id or task produces validation errors."""
        pipeline = make_pipeline(
            nodes=[
                make_node("t1", "trigger"),
                make_node("a1", "agent"),  # no agent_id, no task
            ],
            edges=[make_edge("e1", "t1", "a1")],
        )
        errors = validate_pipeline_dag(pipeline)
        assert len(errors) > 0
        assert any("agent_id" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Execution order
# ---------------------------------------------------------------------------

class TestExecutionOrder:
    """Tests for topological execution ordering."""

    def test_execution_order_linear(self):
        """A -> B -> C returns [A, B, C]."""
        pipeline = make_pipeline(
            nodes=[
                make_node("A", "trigger"),
                make_node("B", "action", action="b"),
                make_node("C", "action", action="c"),
            ],
            edges=[
                make_edge("e1", "A", "B"),
                make_edge("e2", "B", "C"),
            ],
        )
        order = get_execution_order(pipeline)
        assert order == ["A", "B", "C"]

    def test_execution_order_branching(self):
        """Trigger -> (Agent1, Agent2) -> Action.
        Trigger first, Action last, Agent1/Agent2 in either order.
        """
        pipeline = make_pipeline(
            nodes=[
                make_node("trigger", "trigger"),
                make_node("agent1", "agent", agent_id="a1", task="t1"),
                make_node("agent2", "agent", agent_id="a2", task="t2"),
                make_node("action", "action", action="merge"),
            ],
            edges=[
                make_edge("e1", "trigger", "agent1"),
                make_edge("e2", "trigger", "agent2"),
                make_edge("e3", "agent1", "action"),
                make_edge("e4", "agent2", "action"),
            ],
        )
        order = get_execution_order(pipeline)
        assert order[0] == "trigger"
        assert order[-1] == "action"
        assert set(order[1:3]) == {"agent1", "agent2"}


# ---------------------------------------------------------------------------
# JSONB parsing
# ---------------------------------------------------------------------------

class TestParsePipelineDefinition:
    """Tests for parse_pipeline_definition (raw dict -> PipelineDefinition)."""

    def test_parse_pipeline_definition_from_jsonb(self):
        """Parse raw dicts matching JSONB format into PipelineDefinition."""
        nodes_json = [
            {"id": "t1", "type": "trigger", "name": "Start", "config": {}},
            {"id": "a1", "type": "agent", "name": "Agent", "config": {"agent_id": "x", "task": "y"}},
        ]
        edges_json = [
            {"id": "e1", "from": "t1", "to": "a1"},
        ]
        definition = parse_pipeline_definition(nodes_json, edges_json)
        assert len(definition.nodes) == 2
        assert len(definition.edges) == 1
        assert definition.edges[0].from_node == "t1"
        assert definition.edges[0].to_node == "a1"

    def test_parse_pipeline_definition_invalid(self):
        """Raw dicts with missing fields raise ValueError."""
        # Missing required 'id' field
        nodes_json = [{"type": "trigger", "name": "Start"}]
        edges_json = []
        with pytest.raises(ValueError, match="Invalid node data"):
            parse_pipeline_definition(nodes_json, edges_json)

    def test_parse_pipeline_definition_invalid_edge(self):
        """Raw edge dicts with missing fields raise ValueError."""
        nodes_json = [{"id": "t1", "type": "trigger", "name": "Start", "config": {}}]
        edges_json = [{"id": "e1"}]  # Missing 'from' and 'to'
        with pytest.raises(ValueError, match="Invalid edge data"):
            parse_pipeline_definition(nodes_json, edges_json)


# ---------------------------------------------------------------------------
# PipelineEdge alias handling
# ---------------------------------------------------------------------------

class TestPipelineEdgeAlias:
    """Tests for PipelineEdge 'from'/'to' JSON aliases."""

    def test_pipeline_edge_from_alias(self):
        """PipelineEdge 'from'/'to' JSON aliases work correctly."""
        edge = PipelineEdge(id="e1", **{"from": "node_a", "to": "node_b"})
        assert edge.from_node == "node_a"
        assert edge.to_node == "node_b"

    def test_pipeline_edge_by_field_name(self):
        """PipelineEdge can also be constructed using field names."""
        edge = PipelineEdge(id="e1", from_node="node_a", to_node="node_b")
        assert edge.from_node == "node_a"
        assert edge.to_node == "node_b"

    def test_pipeline_edge_serialization_uses_alias(self):
        """PipelineEdge serialization with by_alias uses 'from'/'to'."""
        edge = PipelineEdge(id="e1", from_node="node_a", to_node="node_b")
        data = edge.model_dump(by_alias=True)
        assert data["from"] == "node_a"
        assert data["to"] == "node_b"
