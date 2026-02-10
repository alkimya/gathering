"""
Pydantic models for pipeline definition, nodes, edges, and execution results.

These models parse the existing JSONB node/edge structure stored in
circle.pipelines (nodes and edges columns).
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PipelineEdge(BaseModel):
    """An edge connecting two pipeline nodes.

    JSON keys use "from" and "to" (reserved words in Python),
    mapped to from_node and to_node attributes.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    condition: Optional[str] = None


class PipelineNode(BaseModel):
    """A node in a pipeline DAG.

    Supports node types: trigger, agent, condition, action, parallel, delay.
    Config is stored as a generic dict -- type-specific validation
    is handled by the validator using the typed config models below.
    """

    id: str
    type: Literal["trigger", "agent", "condition", "action", "parallel", "delay"]
    name: str
    config: dict = Field(default_factory=dict)
    position: Optional[dict] = None
    next: Optional[list[str]] = None


class AgentNodeConfig(BaseModel):
    """Configuration for agent-type nodes."""

    agent_id: str
    task: str


class ConditionNodeConfig(BaseModel):
    """Configuration for condition-type nodes."""

    condition: str = "true"


class ActionNodeConfig(BaseModel):
    """Configuration for action-type nodes."""

    model_config = ConfigDict(extra="allow")

    action: str


class DelayNodeConfig(BaseModel):
    """Configuration for delay-type nodes."""

    seconds: float = Field(default=0, ge=0)


class PipelineDefinition(BaseModel):
    """Complete pipeline definition with nodes and edges.

    Parses the JSONB structure from circle.pipelines table.
    """

    nodes: list[PipelineNode]
    edges: list[PipelineEdge]

    @property
    def node_map(self) -> dict[str, PipelineNode]:
        """Return a dict mapping node ID to PipelineNode."""
        return {node.id: node for node in self.nodes}


class NodeExecutionResult(BaseModel):
    """Result of executing a single pipeline node."""

    node_id: str
    status: Literal["completed", "failed", "skipped", "cancelled"]
    output: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: int = 0
    retry_count: int = 0
