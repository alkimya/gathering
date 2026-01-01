"""
Schedules Skill for GatheRing.

Allows agents to schedule actions for future execution.
Supports cron expressions, intervals, and one-time scheduling.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class SchedulesSkill(BaseSkill):
    """
    Skill for managing scheduled actions in GatheRing.

    Agents can:
    - Schedule one-time actions for the future
    - Create recurring actions with cron or intervals
    - List and manage scheduled actions
    - Cancel or update schedules
    """

    name = "schedules"
    description = "Schedule actions for future execution in GatheRing"
    version = "1.0.0"
    required_permissions = [SkillPermission.EXECUTE]

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
                "name": "schedule_create",
                "description": "Schedule an action for future execution.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name for this scheduled action"
                        },
                        "action_type": {
                            "type": "string",
                            "description": "Type of action: run_task, send_notification, call_api, execute_pipeline"
                        },
                        "action_config": {
                            "type": "object",
                            "description": "Configuration for the action (agent_id, goal, etc.)"
                        },
                        "schedule_type": {
                            "type": "string",
                            "enum": ["once", "cron", "interval"],
                            "description": "Type of schedule"
                        },
                        "cron_expression": {
                            "type": "string",
                            "description": "Cron expression for recurring schedules (e.g., '0 9 * * 1' for Mondays at 9am)"
                        },
                        "interval_seconds": {
                            "type": "integer",
                            "description": "Interval in seconds for recurring execution"
                        },
                        "run_at": {
                            "type": "string",
                            "description": "ISO datetime for one-time execution"
                        },
                        "max_executions": {
                            "type": "integer",
                            "description": "Maximum number of times to execute (null for unlimited)"
                        },
                        "enabled": {
                            "type": "boolean",
                            "description": "Whether the schedule is enabled",
                            "default": True
                        }
                    },
                    "required": ["name", "action_type", "action_config", "schedule_type"]
                }
            },
            {
                "name": "schedule_list",
                "description": "List scheduled actions.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "enabled_only": {
                            "type": "boolean",
                            "description": "Only show enabled schedules"
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
                "name": "schedule_get",
                "description": "Get details of a specific scheduled action.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {
                            "type": "integer",
                            "description": "ID of the schedule"
                        }
                    },
                    "required": ["schedule_id"]
                }
            },
            {
                "name": "schedule_update",
                "description": "Update a scheduled action.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {
                            "type": "integer",
                            "description": "ID of the schedule to update"
                        },
                        "enabled": {
                            "type": "boolean",
                            "description": "Enable or disable the schedule"
                        },
                        "name": {
                            "type": "string",
                            "description": "New name"
                        },
                        "cron_expression": {
                            "type": "string",
                            "description": "New cron expression"
                        },
                        "interval_seconds": {
                            "type": "integer",
                            "description": "New interval"
                        }
                    },
                    "required": ["schedule_id"]
                }
            },
            {
                "name": "schedule_delete",
                "description": "Delete a scheduled action.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {
                            "type": "integer",
                            "description": "ID of the schedule to delete"
                        }
                    },
                    "required": ["schedule_id"]
                }
            },
            {
                "name": "schedule_run_now",
                "description": "Trigger immediate execution of a scheduled action.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {
                            "type": "integer",
                            "description": "ID of the schedule to run"
                        }
                    },
                    "required": ["schedule_id"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a schedule tool synchronously."""
        self.ensure_initialized()

        try:
            if tool_name == "schedule_create":
                return self._create_schedule(tool_input)
            elif tool_name == "schedule_list":
                return self._list_schedules(tool_input)
            elif tool_name == "schedule_get":
                return self._get_schedule(tool_input)
            elif tool_name == "schedule_update":
                return self._update_schedule(tool_input)
            elif tool_name == "schedule_delete":
                return self._delete_schedule(tool_input)
            elif tool_name == "schedule_run_now":
                return self._run_now(tool_input)
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

    def _create_schedule(self, params: Dict[str, Any]) -> SkillResponse:
        """Create a new scheduled action."""
        import json
        from datetime import datetime

        schedule_type = params["schedule_type"]

        # Calculate next run time
        next_run = None
        if schedule_type == "once" and params.get("run_at"):
            next_run = params["run_at"]
        elif schedule_type == "interval":
            # Next run is now + interval
            from datetime import timedelta
            next_run = (datetime.utcnow() + timedelta(seconds=params.get("interval_seconds", 3600))).isoformat()
        elif schedule_type == "cron" and params.get("cron_expression"):
            # Calculate from cron
            try:
                from croniter import croniter
                cron = croniter(params["cron_expression"], datetime.utcnow())
                next_run = cron.get_next(datetime).isoformat()
            except Exception:
                next_run = None

        result = self._db_service.execute(
            """
            INSERT INTO circle.scheduled_actions
            (name, action_type, action_config, schedule_type, cron_expression,
             interval_seconds, next_run, max_executions, is_enabled)
            VALUES (%(name)s, %(action_type)s, %(action_config)s::jsonb, %(schedule_type)s,
                    %(cron_expression)s, %(interval_seconds)s, %(next_run)s,
                    %(max_executions)s, %(enabled)s)
            RETURNING id, name, action_type, schedule_type, next_run, is_enabled
            """,
            {
                "name": params["name"],
                "action_type": params["action_type"],
                "action_config": json.dumps(params["action_config"]),
                "schedule_type": schedule_type,
                "cron_expression": params.get("cron_expression"),
                "interval_seconds": params.get("interval_seconds"),
                "next_run": next_run,
                "max_executions": params.get("max_executions"),
                "enabled": params.get("enabled", True),
            }
        )

        if result:
            schedule = result[0]
            return SkillResponse(
                success=True,
                message=f"Schedule created: {schedule['name']} (ID: {schedule['id']})",
                data=self._serialize_row(schedule),
                skill_name=self.name,
                tool_name="schedule_create",
            )

        return SkillResponse(
            success=False,
            message="Failed to create schedule",
            error="creation_failed",
            skill_name=self.name,
            tool_name="schedule_create",
        )

    def _list_schedules(self, params: Dict[str, Any]) -> SkillResponse:
        """List scheduled actions."""
        enabled_only = params.get("enabled_only", False)
        limit = params.get("limit", 20)

        if enabled_only:
            result = self._db_service.execute(
                """
                SELECT id, name, action_type, schedule_type, cron_expression,
                       interval_seconds, next_run, last_run, execution_count,
                       max_executions, is_enabled, created_at
                FROM circle.scheduled_actions
                WHERE is_enabled = true
                ORDER BY next_run ASC NULLS LAST
                LIMIT %(limit)s
                """,
                {"limit": limit}
            )
        else:
            result = self._db_service.execute(
                """
                SELECT id, name, action_type, schedule_type, cron_expression,
                       interval_seconds, next_run, last_run, execution_count,
                       max_executions, is_enabled, created_at
                FROM circle.scheduled_actions
                ORDER BY created_at DESC
                LIMIT %(limit)s
                """,
                {"limit": limit}
            )

        schedules = [self._serialize_row(r) for r in result] if result else []

        return SkillResponse(
            success=True,
            message=f"Found {len(schedules)} schedules",
            data=schedules,
            skill_name=self.name,
            tool_name="schedule_list",
        )

    def _get_schedule(self, params: Dict[str, Any]) -> SkillResponse:
        """Get a specific schedule."""
        result = self._db_service.execute(
            """
            SELECT id, name, action_type, action_config, schedule_type,
                   cron_expression, interval_seconds, next_run, last_run,
                   execution_count, max_executions, is_enabled,
                   last_error, created_at, updated_at
            FROM circle.scheduled_actions
            WHERE id = %(id)s
            """,
            {"id": params["schedule_id"]}
        )

        if not result:
            return SkillResponse(
                success=False,
                message=f"Schedule {params['schedule_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="schedule_get",
            )

        return SkillResponse(
            success=True,
            message=f"Schedule: {result[0]['name']}",
            data=self._serialize_row(result[0]),
            skill_name=self.name,
            tool_name="schedule_get",
        )

    def _update_schedule(self, params: Dict[str, Any]) -> SkillResponse:
        """Update a schedule."""
        updates = []
        values = {"id": params["schedule_id"]}

        if "enabled" in params:
            updates.append("is_enabled = %(enabled)s")
            values["enabled"] = params["enabled"]
        if "name" in params:
            updates.append("name = %(name)s")
            values["name"] = params["name"]
        if "cron_expression" in params:
            updates.append("cron_expression = %(cron_expression)s")
            values["cron_expression"] = params["cron_expression"]
        if "interval_seconds" in params:
            updates.append("interval_seconds = %(interval_seconds)s")
            values["interval_seconds"] = params["interval_seconds"]

        if not updates:
            return SkillResponse(
                success=False,
                message="No updates provided",
                error="no_updates",
                skill_name=self.name,
                tool_name="schedule_update",
            )

        updates.append("updated_at = CURRENT_TIMESTAMP")

        result = self._db_service.execute(
            f"""
            UPDATE circle.scheduled_actions
            SET {', '.join(updates)}
            WHERE id = %(id)s
            RETURNING id, name, is_enabled, updated_at
            """,
            values
        )

        if result:
            return SkillResponse(
                success=True,
                message=f"Schedule updated: {result[0]['name']}",
                data=self._serialize_row(result[0]),
                skill_name=self.name,
                tool_name="schedule_update",
            )

        return SkillResponse(
            success=False,
            message=f"Schedule {params['schedule_id']} not found",
            error="not_found",
            skill_name=self.name,
            tool_name="schedule_update",
        )

    def _delete_schedule(self, params: Dict[str, Any]) -> SkillResponse:
        """Delete a schedule."""
        result = self._db_service.execute(
            """
            DELETE FROM circle.scheduled_actions
            WHERE id = %(id)s
            RETURNING id, name
            """,
            {"id": params["schedule_id"]}
        )

        if result:
            return SkillResponse(
                success=True,
                message=f"Schedule deleted: {result[0]['name']}",
                data={"id": result[0]["id"]},
                skill_name=self.name,
                tool_name="schedule_delete",
            )

        return SkillResponse(
            success=False,
            message=f"Schedule {params['schedule_id']} not found",
            error="not_found",
            skill_name=self.name,
            tool_name="schedule_delete",
        )

    def _run_now(self, params: Dict[str, Any]) -> SkillResponse:
        """Trigger immediate execution of a schedule."""
        # Get schedule
        result = self._db_service.execute(
            """
            SELECT id, name, action_type, action_config
            FROM circle.scheduled_actions
            WHERE id = %(id)s
            """,
            {"id": params["schedule_id"]}
        )

        if not result:
            return SkillResponse(
                success=False,
                message=f"Schedule {params['schedule_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="schedule_run_now",
            )

        schedule = result[0]

        # Update last_run and execution_count
        self._db_service.execute(
            """
            UPDATE circle.scheduled_actions
            SET last_run = CURRENT_TIMESTAMP,
                execution_count = execution_count + 1
            WHERE id = %(id)s
            """,
            {"id": params["schedule_id"]}
        )

        # TODO: Actually execute the action based on action_type
        # For now, just log that it was triggered

        return SkillResponse(
            success=True,
            message=f"Schedule triggered: {schedule['name']}",
            data={
                "id": schedule["id"],
                "name": schedule["name"],
                "action_type": schedule["action_type"],
                "triggered_at": datetime.utcnow().isoformat(),
            },
            skill_name=self.name,
            tool_name="schedule_run_now",
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
