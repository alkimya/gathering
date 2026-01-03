"""
Pipelines Skill for GatheRing.

Allows agents to create, manage, and run automated workflows.
Pipelines connect multiple agents and actions in a sequence.
"""

from typing import Any, Dict, List, Optional
import logging

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class PipelinesSkill(BaseSkill):
    """
    Skill for managing GatheRing pipelines.

    Agents can:
    - Create new pipelines with nodes and edges
    - List and get pipeline details
    - Run pipelines manually
    - Update pipeline status
    """

    name = "pipelines"
    description = "Create and manage automated workflow pipelines in GatheRing"
    version = "1.0.0"
    required_permissions = [SkillPermission.WRITE, SkillPermission.EXECUTE]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._db_service = None

    def initialize(self) -> None:
        """Lazy initialization - get DB service."""
        from gathering.api.dependencies import get_database_service
        self._db_service = get_database_service()
        self._initialized = True

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """Return tool definitions for LLM."""
        return [
            {
                "name": "pipeline_create",
                "description": "Create a new workflow pipeline. Pipelines automate multi-step processes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Pipeline name"
                        },
                        "description": {
                            "type": "string",
                            "description": "What this pipeline does"
                        },
                        "nodes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "type": {
                                        "type": "string",
                                        "enum": ["trigger", "agent", "condition", "action", "parallel", "delay"]
                                    },
                                    "name": {"type": "string"},
                                    "config": {"type": "object"}
                                },
                                "required": ["id", "type", "name"]
                            },
                            "description": "Pipeline nodes"
                        },
                        "edges": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "from": {"type": "string"},
                                    "to": {"type": "string"},
                                    "condition": {"type": "string"}
                                },
                                "required": ["id", "from", "to"]
                            },
                            "description": "Connections between nodes"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "paused", "draft"],
                            "description": "Initial status (default: draft)"
                        }
                    },
                    "required": ["name", "description"]
                }
            },
            {
                "name": "pipeline_list",
                "description": "List available pipelines.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["active", "paused", "draft"],
                            "description": "Filter by status"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 20
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "pipeline_get",
                "description": "Get details of a specific pipeline.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pipeline_id": {
                            "type": "integer",
                            "description": "ID of the pipeline"
                        }
                    },
                    "required": ["pipeline_id"]
                }
            },
            {
                "name": "pipeline_run",
                "description": "Trigger a pipeline run.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pipeline_id": {
                            "type": "integer",
                            "description": "ID of the pipeline to run"
                        },
                        "trigger_data": {
                            "type": "object",
                            "description": "Input data for the pipeline run"
                        }
                    },
                    "required": ["pipeline_id"]
                }
            },
            {
                "name": "pipeline_update",
                "description": "Update a pipeline's status or configuration.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pipeline_id": {
                            "type": "integer",
                            "description": "ID of the pipeline to update"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "paused", "draft"],
                            "description": "New status"
                        },
                        "name": {
                            "type": "string",
                            "description": "New name"
                        },
                        "description": {
                            "type": "string",
                            "description": "New description"
                        }
                    },
                    "required": ["pipeline_id"]
                }
            },
            {
                "name": "pipeline_runs",
                "description": "List recent runs for a pipeline.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pipeline_id": {
                            "type": "integer",
                            "description": "ID of the pipeline"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    },
                    "required": ["pipeline_id"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a pipeline tool synchronously."""
        self.ensure_initialized()

        try:
            if tool_name == "pipeline_create":
                return self._create_pipeline(tool_input)
            elif tool_name == "pipeline_list":
                return self._list_pipelines(tool_input)
            elif tool_name == "pipeline_get":
                return self._get_pipeline(tool_input)
            elif tool_name == "pipeline_run":
                return self._run_pipeline(tool_input)
            elif tool_name == "pipeline_update":
                return self._update_pipeline(tool_input)
            elif tool_name == "pipeline_runs":
                return self._list_runs(tool_input)
            else:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool",
                    skill_name=self.name,
                    tool_name=tool_name,
                )
        except Exception as e:
            logger.exception(f"Error in {tool_name}")
            return SkillResponse(
                success=False,
                message=f"Error: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name=tool_name,
            )

    def _create_pipeline(self, params: Dict[str, Any]) -> SkillResponse:
        """Create a new pipeline."""
        import json

        nodes = params.get("nodes", [])
        edges = params.get("edges", [])

        result = self._db_service.execute(
            """
            INSERT INTO circle.pipelines (name, description, status, nodes, edges)
            VALUES (%(name)s, %(description)s, %(status)s, %(nodes)s::jsonb, %(edges)s::jsonb)
            RETURNING id, name, status, created_at
            """,
            {
                "name": params["name"],
                "description": params.get("description", ""),
                "status": params.get("status", "draft"),
                "nodes": json.dumps(nodes),
                "edges": json.dumps(edges),
            }
        )

        if result:
            pipeline = result[0]
            return SkillResponse(
                success=True,
                message=f"Pipeline created: {pipeline['name']} (ID: {pipeline['id']})",
                data=self._serialize_row(pipeline),
                skill_name=self.name,
                tool_name="pipeline_create",
            )

        return SkillResponse(
            success=False,
            message="Failed to create pipeline",
            error="creation_failed",
            skill_name=self.name,
            tool_name="pipeline_create",
        )

    def _list_pipelines(self, params: Dict[str, Any]) -> SkillResponse:
        """List pipelines."""
        status = params.get("status")
        limit = params.get("limit", 20)

        if status:
            result = self._db_service.execute(
                """
                SELECT id, name, description, status, run_count, success_count, error_count,
                       created_at, updated_at, last_run
                FROM circle.pipelines
                WHERE status = %(status)s
                ORDER BY updated_at DESC
                LIMIT %(limit)s
                """,
                {"status": status, "limit": limit}
            )
        else:
            result = self._db_service.execute(
                """
                SELECT id, name, description, status, run_count, success_count, error_count,
                       created_at, updated_at, last_run
                FROM circle.pipelines
                ORDER BY updated_at DESC
                LIMIT %(limit)s
                """,
                {"limit": limit}
            )

        pipelines = [self._serialize_row(r) for r in result] if result else []

        return SkillResponse(
            success=True,
            message=f"Found {len(pipelines)} pipelines",
            data=pipelines,
            skill_name=self.name,
            tool_name="pipeline_list",
        )

    def _get_pipeline(self, params: Dict[str, Any]) -> SkillResponse:
        """Get a specific pipeline."""
        result = self._db_service.execute(
            """
            SELECT id, name, description, status, nodes, edges,
                   run_count, success_count, error_count,
                   created_at, updated_at, last_run
            FROM circle.pipelines
            WHERE id = %(id)s
            """,
            {"id": params["pipeline_id"]}
        )

        if not result:
            return SkillResponse(
                success=False,
                message=f"Pipeline {params['pipeline_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="pipeline_get",
            )

        return SkillResponse(
            success=True,
            message=f"Pipeline: {result[0]['name']}",
            data=self._serialize_row(result[0]),
            skill_name=self.name,
            tool_name="pipeline_get",
        )

    def _run_pipeline(self, params: Dict[str, Any]) -> SkillResponse:
        """Trigger a pipeline run."""
        import json

        # Get pipeline
        pipeline = self._db_service.execute(
            "SELECT id, name, status FROM circle.pipelines WHERE id = %(id)s",
            {"id": params["pipeline_id"]}
        )

        if not pipeline:
            return SkillResponse(
                success=False,
                message=f"Pipeline {params['pipeline_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="pipeline_run",
            )

        if pipeline[0]["status"] != "active":
            return SkillResponse(
                success=False,
                message=f"Pipeline is not active (status: {pipeline[0]['status']})",
                error="not_active",
                skill_name=self.name,
                tool_name="pipeline_run",
            )

        # Create run
        trigger_data = params.get("trigger_data", {})
        result = self._db_service.execute(
            """
            INSERT INTO circle.pipeline_runs (pipeline_id, status, trigger_data, started_at)
            VALUES (%(pipeline_id)s, 'running', %(trigger_data)s::jsonb, CURRENT_TIMESTAMP)
            RETURNING id, pipeline_id, status, started_at
            """,
            {
                "pipeline_id": params["pipeline_id"],
                "trigger_data": json.dumps(trigger_data),
            }
        )

        if result:
            # Update pipeline run count
            self._db_service.execute(
                """
                UPDATE circle.pipelines
                SET run_count = run_count + 1, last_run = CURRENT_TIMESTAMP
                WHERE id = %(id)s
                """,
                {"id": params["pipeline_id"]}
            )

            return SkillResponse(
                success=True,
                message=f"Pipeline run started (Run ID: {result[0]['id']})",
                data=self._serialize_row(result[0]),
                skill_name=self.name,
                tool_name="pipeline_run",
            )

        return SkillResponse(
            success=False,
            message="Failed to start pipeline run",
            error="run_failed",
            skill_name=self.name,
            tool_name="pipeline_run",
        )

    def _update_pipeline(self, params: Dict[str, Any]) -> SkillResponse:
        """Update a pipeline."""
        updates = []
        values = {"id": params["pipeline_id"]}

        if "status" in params:
            updates.append("status = %(status)s")
            values["status"] = params["status"]
        if "name" in params:
            updates.append("name = %(name)s")
            values["name"] = params["name"]
        if "description" in params:
            updates.append("description = %(description)s")
            values["description"] = params["description"]

        if not updates:
            return SkillResponse(
                success=False,
                message="No updates provided",
                error="no_updates",
                skill_name=self.name,
                tool_name="pipeline_update",
            )

        updates.append("updated_at = CURRENT_TIMESTAMP")

        result = self._db_service.execute(
            f"""
            UPDATE circle.pipelines
            SET {', '.join(updates)}
            WHERE id = %(id)s
            RETURNING id, name, status, updated_at
            """,
            values
        )

        if result:
            return SkillResponse(
                success=True,
                message=f"Pipeline updated: {result[0]['name']}",
                data=self._serialize_row(result[0]),
                skill_name=self.name,
                tool_name="pipeline_update",
            )

        return SkillResponse(
            success=False,
            message=f"Pipeline {params['pipeline_id']} not found",
            error="not_found",
            skill_name=self.name,
            tool_name="pipeline_update",
        )

    def _list_runs(self, params: Dict[str, Any]) -> SkillResponse:
        """List pipeline runs."""
        result = self._db_service.execute(
            """
            SELECT id, pipeline_id, status, started_at, completed_at,
                   current_node, error_message, duration_seconds
            FROM circle.pipeline_runs
            WHERE pipeline_id = %(pipeline_id)s
            ORDER BY started_at DESC
            LIMIT %(limit)s
            """,
            {
                "pipeline_id": params["pipeline_id"],
                "limit": params.get("limit", 10),
            }
        )

        runs = [self._serialize_row(r) for r in result] if result else []

        return SkillResponse(
            success=True,
            message=f"Found {len(runs)} runs",
            data=runs,
            skill_name=self.name,
            tool_name="pipeline_runs",
        )

    def _serialize_row(self, row: dict) -> dict:
        """Convert database row to JSON-serializable dict."""
        result = {}
        for key, value in row.items():
            if hasattr(value, 'isoformat'):
                result[key] = value.isoformat()
            elif isinstance(value, (list, tuple)):
                result[key] = list(value) if value else []
            else:
                result[key] = value
        return result
