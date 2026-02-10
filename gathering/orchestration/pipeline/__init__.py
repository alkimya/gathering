"""
Pipeline execution package.

Provides pipeline DAG validation, Pydantic models for pipeline definition,
execution engine, node dispatchers, and circuit breaker.

Usage:
    from gathering.orchestration.pipeline import (
        PipelineExecutor,
        CircuitBreaker,
        CircuitState,
        NodeExecutionError,
        NodeConfigError,
        dispatch_node,
        validate_pipeline_dag,
        get_execution_order,
        parse_pipeline_definition,
        PipelineDefinition,
        PipelineNode,
        PipelineEdge,
        NodeExecutionResult,
    )
"""

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
    NodeExecutionResult,
    PipelineDefinition,
    PipelineEdge,
    PipelineNode,
)
from gathering.orchestration.pipeline.nodes import (
    NodeConfigError,
    NodeExecutionError,
    dispatch_node,
)
from gathering.orchestration.pipeline.validator import (
    get_execution_order,
    parse_pipeline_definition,
    validate_pipeline_dag,
)

__all__ = [
    "PipelineExecutor",
    "PipelineRunManager",
    "get_run_manager",
    "CircuitBreaker",
    "CircuitState",
    "NodeExecutionError",
    "NodeConfigError",
    "dispatch_node",
    "validate_pipeline_dag",
    "get_execution_order",
    "parse_pipeline_definition",
    "PipelineDefinition",
    "PipelineNode",
    "PipelineEdge",
    "NodeExecutionResult",
]
