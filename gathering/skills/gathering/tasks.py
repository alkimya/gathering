"""
Background Tasks Skill for GatheRing.

Allows agents to start and manage long-running autonomous tasks.
Tasks execute goals in the background and report progress.
"""

from typing import Any, Dict, List, Optional
import logging

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class BackgroundTasksSkill(BaseSkill):
    """
    Skill for managing GatheRing background tasks.

    Agents can:
    - Start new background tasks
    - List running and completed tasks
    - Pause, resume, or cancel tasks
    - Get task progress and steps
    """

    name = "tasks"
    description = "Start and manage long-running background tasks in GatheRing"
    version = "1.0.0"
    required_permissions = [SkillPermission.EXECUTE]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._db_service = None
        self._executor = None

    def initialize(self) -> None:
        """Lazy initialization - get services."""
        from gathering.api.dependencies import get_database_service
        from gathering.orchestration.background import get_background_executor

        self._db_service = get_database_service()
        self._executor = get_background_executor()
        self._initialized = True

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """Return tool definitions for LLM."""
        return [
            {
                "name": "task_start",
                "description": "Start a new background task to work on a goal autonomously.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "integer",
                            "description": "ID of the agent to execute the task"
                        },
                        "goal": {
                            "type": "string",
                            "description": "What the task should accomplish"
                        },
                        "goal_id": {
                            "type": "integer",
                            "description": "Optional: Link to an existing goal"
                        },
                        "context": {
                            "type": "object",
                            "description": "Additional context for the task"
                        },
                        "max_steps": {
                            "type": "integer",
                            "description": "Maximum execution steps (default: 50)",
                            "default": 50
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 3600 = 1 hour)",
                            "default": 3600
                        }
                    },
                    "required": ["agent_id", "goal"]
                }
            },
            {
                "name": "task_list",
                "description": "List background tasks with optional filters.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "running", "paused", "completed", "failed", "timeout", "cancelled"],
                            "description": "Filter by status"
                        },
                        "agent_id": {
                            "type": "integer",
                            "description": "Filter by agent ID"
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
                "name": "task_get",
                "description": "Get details of a specific task.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "ID of the task"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "task_steps",
                "description": "Get execution steps for a task.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "ID of the task"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of steps",
                            "default": 20
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "task_pause",
                "description": "Pause a running task.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "ID of the task to pause"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "task_resume",
                "description": "Resume a paused task.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "ID of the task to resume"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "task_cancel",
                "description": "Cancel a running or paused task.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "ID of the task to cancel"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for cancellation"
                        }
                    },
                    "required": ["task_id"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a task tool synchronously."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self.execute_async(tool_name, tool_input),
                    loop
                )
                return future.result(timeout=30)
            else:
                return loop.run_until_complete(self.execute_async(tool_name, tool_input))
        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Error executing {tool_name}: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name=tool_name,
            )

    async def execute_async(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a task tool asynchronously."""
        self.ensure_initialized()

        try:
            if tool_name == "task_start":
                return await self._start_task(tool_input)
            elif tool_name == "task_list":
                return await self._list_tasks(tool_input)
            elif tool_name == "task_get":
                return await self._get_task(tool_input)
            elif tool_name == "task_steps":
                return await self._get_steps(tool_input)
            elif tool_name == "task_pause":
                return await self._pause_task(tool_input)
            elif tool_name == "task_resume":
                return await self._resume_task(tool_input)
            elif tool_name == "task_cancel":
                return await self._cancel_task(tool_input)
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

    async def _start_task(self, params: Dict[str, Any]) -> SkillResponse:
        """Start a new background task."""
        from gathering.orchestration.background import BackgroundTask

        task = BackgroundTask(
            id=0,  # Will be assigned by DB
            agent_id=params["agent_id"],
            goal=params["goal"],
            goal_id=params.get("goal_id"),
            goal_context=params.get("context", {}),
            max_steps=params.get("max_steps", 50),
            timeout_seconds=params.get("timeout_seconds", 3600),
            checkpoint_interval=params.get("checkpoint_interval", 5),
        )

        # Start the task
        started_task = await self._executor.start_task(task)

        return SkillResponse(
            success=True,
            message=f"Task started (ID: {started_task.id}): {started_task.goal[:50]}...",
            data={
                "id": started_task.id,
                "agent_id": started_task.agent_id,
                "goal": started_task.goal,
                "status": started_task.status.value,
                "max_steps": started_task.max_steps,
            },
            skill_name=self.name,
            tool_name="task_start",
        )

    async def _list_tasks(self, params: Dict[str, Any]) -> SkillResponse:
        """List background tasks."""
        status = params.get("status")
        agent_id = params.get("agent_id")
        limit = params.get("limit", 20)

        sql = "SELECT * FROM public.background_tasks_dashboard WHERE 1=1"
        sql_params = {}

        if status:
            sql += " AND status = %(status)s"
            sql_params["status"] = status
        if agent_id:
            sql += " AND agent_id = %(agent_id)s"
            sql_params["agent_id"] = agent_id

        sql += " ORDER BY created_at DESC LIMIT %(limit)s"
        sql_params["limit"] = limit

        result = self._db_service.execute(sql, sql_params)
        tasks = [self._serialize_row(r) for r in result] if result else []

        return SkillResponse(
            success=True,
            message=f"Found {len(tasks)} tasks",
            data=tasks,
            skill_name=self.name,
            tool_name="task_list",
        )

    async def _get_task(self, params: Dict[str, Any]) -> SkillResponse:
        """Get a specific task."""
        result = self._db_service.execute(
            "SELECT * FROM public.background_tasks_dashboard WHERE id = %(id)s",
            {"id": params["task_id"]}
        )

        if not result:
            return SkillResponse(
                success=False,
                message=f"Task {params['task_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="task_get",
            )

        return SkillResponse(
            success=True,
            message=f"Task: {result[0]['goal'][:50]}...",
            data=self._serialize_row(result[0]),
            skill_name=self.name,
            tool_name="task_get",
        )

    async def _get_steps(self, params: Dict[str, Any]) -> SkillResponse:
        """Get task execution steps."""
        result = self._db_service.execute(
            """
            SELECT id, task_id, step_number, action_type, action_input,
                   action_output, tool_name, success, error_message,
                   tokens_input, tokens_output, duration_ms, created_at
            FROM agent.task_steps
            WHERE task_id = %(task_id)s
            ORDER BY step_number DESC
            LIMIT %(limit)s
            """,
            {
                "task_id": params["task_id"],
                "limit": params.get("limit", 20),
            }
        )

        steps = [self._serialize_row(r) for r in result] if result else []

        return SkillResponse(
            success=True,
            message=f"Found {len(steps)} steps",
            data=steps,
            skill_name=self.name,
            tool_name="task_steps",
        )

    async def _pause_task(self, params: Dict[str, Any]) -> SkillResponse:
        """Pause a running task."""
        try:
            await self._executor.pause_task(params["task_id"])
            return SkillResponse(
                success=True,
                message=f"Task {params['task_id']} paused",
                data={"task_id": params["task_id"], "status": "paused"},
                skill_name=self.name,
                tool_name="task_pause",
            )
        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Failed to pause task: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name="task_pause",
            )

    async def _resume_task(self, params: Dict[str, Any]) -> SkillResponse:
        """Resume a paused task."""
        try:
            await self._executor.resume_task(params["task_id"])
            return SkillResponse(
                success=True,
                message=f"Task {params['task_id']} resumed",
                data={"task_id": params["task_id"], "status": "running"},
                skill_name=self.name,
                tool_name="task_resume",
            )
        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Failed to resume task: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name="task_resume",
            )

    async def _cancel_task(self, params: Dict[str, Any]) -> SkillResponse:
        """Cancel a task."""
        try:
            await self._executor.cancel_task(
                params["task_id"],
                reason=params.get("reason", "Cancelled by agent")
            )
            return SkillResponse(
                success=True,
                message=f"Task {params['task_id']} cancelled",
                data={"task_id": params["task_id"], "status": "cancelled"},
                skill_name=self.name,
                tool_name="task_cancel",
            )
        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Failed to cancel task: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name="task_cancel",
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
