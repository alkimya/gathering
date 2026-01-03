"""
Goals Skill for GatheRing.

Allows agents to create, manage, and track goals within the GatheRing system.
Goals are visible in the dashboard and enable autonomous agent workflows.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class GoalsSkill(BaseSkill):
    """
    Skill for managing GatheRing goals.

    Agents can:
    - Create new goals for themselves or other agents
    - Update goal status and progress
    - List and filter goals
    - Add subgoals (decomposition)
    - Mark goals as complete or failed
    """

    name = "goals"
    description = "Create and manage goals in GatheRing"
    version = "1.0.0"
    required_permissions = [SkillPermission.WRITE]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._db_service = None
        self._goal_manager = None

    def initialize(self) -> None:
        """Lazy initialization - get DB service."""
        from gathering.api.dependencies import get_database_service
        from gathering.agents.goals import get_goal_manager

        self._db_service = get_database_service()
        self._goal_manager = get_goal_manager(db_service=self._db_service)
        self._initialized = True

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """Return tool definitions for LLM."""
        return [
            {
                "name": "goal_create",
                "description": "Create a new goal. Goals track objectives and appear in the dashboard.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short title for the goal"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of what needs to be accomplished"
                        },
                        "agent_id": {
                            "type": "integer",
                            "description": "ID of the agent responsible (use your own ID if for yourself)"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "Goal priority level"
                        },
                        "parent_id": {
                            "type": "integer",
                            "description": "Parent goal ID if this is a subgoal"
                        },
                        "success_criteria": {
                            "type": "string",
                            "description": "How to know when the goal is complete"
                        },
                        "estimated_hours": {
                            "type": "number",
                            "description": "Estimated hours to complete"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization"
                        }
                    },
                    "required": ["title", "description", "agent_id"]
                }
            },
            {
                "name": "goal_update",
                "description": "Update an existing goal's status, progress, or details.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "goal_id": {
                            "type": "integer",
                            "description": "ID of the goal to update"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "active", "blocked", "paused", "completed", "failed", "cancelled"],
                            "description": "New status"
                        },
                        "progress_percent": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Progress percentage (0-100)"
                        },
                        "status_message": {
                            "type": "string",
                            "description": "Status update message"
                        },
                        "result_summary": {
                            "type": "string",
                            "description": "Summary of results when completing"
                        }
                    },
                    "required": ["goal_id"]
                }
            },
            {
                "name": "goal_list",
                "description": "List goals with optional filters.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "integer",
                            "description": "Filter by agent ID"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "active", "blocked", "paused", "completed", "failed", "cancelled"],
                            "description": "Filter by status"
                        },
                        "parent_id": {
                            "type": "integer",
                            "description": "Filter by parent goal (for subgoals)"
                        },
                        "root_only": {
                            "type": "boolean",
                            "description": "Only return top-level goals (no subgoals)"
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
                "name": "goal_get",
                "description": "Get details of a specific goal.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "goal_id": {
                            "type": "integer",
                            "description": "ID of the goal"
                        }
                    },
                    "required": ["goal_id"]
                }
            },
            {
                "name": "goal_complete",
                "description": "Mark a goal as completed with results.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "goal_id": {
                            "type": "integer",
                            "description": "ID of the goal to complete"
                        },
                        "result_summary": {
                            "type": "string",
                            "description": "Summary of what was accomplished"
                        },
                        "lessons_learned": {
                            "type": "string",
                            "description": "Lessons learned during goal execution"
                        },
                        "artifacts": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Artifacts produced (files, links, data)"
                        }
                    },
                    "required": ["goal_id", "result_summary"]
                }
            },
            {
                "name": "goal_fail",
                "description": "Mark a goal as failed with reason.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "goal_id": {
                            "type": "integer",
                            "description": "ID of the goal"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why the goal failed"
                        },
                        "lessons_learned": {
                            "type": "string",
                            "description": "What can be learned from the failure"
                        }
                    },
                    "required": ["goal_id", "reason"]
                }
            },
            {
                "name": "goal_add_subgoal",
                "description": "Add a subgoal to break down a larger goal.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "integer",
                            "description": "ID of the parent goal"
                        },
                        "title": {
                            "type": "string",
                            "description": "Subgoal title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Subgoal description"
                        },
                        "agent_id": {
                            "type": "integer",
                            "description": "Agent to assign (defaults to parent's agent)"
                        }
                    },
                    "required": ["parent_id", "title", "description"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a goal tool synchronously."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, need to use run_coroutine_threadsafe
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
        """Execute a goal tool asynchronously."""
        self.ensure_initialized()

        try:
            if tool_name == "goal_create":
                return await self._create_goal(tool_input)
            elif tool_name == "goal_update":
                return await self._update_goal(tool_input)
            elif tool_name == "goal_list":
                return await self._list_goals(tool_input)
            elif tool_name == "goal_get":
                return await self._get_goal(tool_input)
            elif tool_name == "goal_complete":
                return await self._complete_goal(tool_input)
            elif tool_name == "goal_fail":
                return await self._fail_goal(tool_input)
            elif tool_name == "goal_add_subgoal":
                return await self._add_subgoal(tool_input)
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

    async def _create_goal(self, params: Dict[str, Any]) -> SkillResponse:
        """Create a new goal."""
        from gathering.agents.goals import GoalPriority
        from decimal import Decimal

        # Calculate depth if parent specified
        depth = 0
        if params.get("parent_id"):
            parent = await self._goal_manager.get_goal(params["parent_id"])
            if parent:
                depth = parent.depth + 1

        goal = await self._goal_manager.create_goal(
            agent_id=params["agent_id"],
            title=params["title"],
            description=params["description"],
            priority=GoalPriority(params.get("priority", "medium")),
            parent_id=params.get("parent_id"),
            depth=depth,
            success_criteria=params.get("success_criteria"),
            estimated_hours=Decimal(str(params["estimated_hours"])) if params.get("estimated_hours") else None,
            tags=params.get("tags", []),
            context=params.get("context", {}),
        )

        return SkillResponse(
            success=True,
            message=f"Goal created: {goal.title} (ID: {goal.id})",
            data=goal.to_dict(),
            skill_name=self.name,
            tool_name="goal_create",
        )

    async def _update_goal(self, params: Dict[str, Any]) -> SkillResponse:
        """Update an existing goal."""
        from gathering.agents.goals import GoalStatus

        goal_id = params["goal_id"]

        # Build update dict
        updates = {}
        if "status" in params:
            updates["status"] = GoalStatus(params["status"])
        if "progress_percent" in params:
            updates["progress_percent"] = params["progress_percent"]
        if "status_message" in params:
            updates["status_message"] = params["status_message"]
        if "result_summary" in params:
            updates["result_summary"] = params["result_summary"]

        goal = await self._goal_manager.update_goal(goal_id, **updates)

        if not goal:
            return SkillResponse(
                success=False,
                message=f"Goal {goal_id} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="goal_update",
            )

        return SkillResponse(
            success=True,
            message=f"Goal updated: {goal.title}",
            data=goal.to_dict(),
            skill_name=self.name,
            tool_name="goal_update",
        )

    async def _list_goals(self, params: Dict[str, Any]) -> SkillResponse:
        """List goals with filters."""
        from gathering.agents.goals import GoalStatus

        status = GoalStatus(params["status"]) if params.get("status") else None

        goals = await self._goal_manager.list_goals(
            agent_id=params.get("agent_id"),
            status=status,
            parent_id=params.get("parent_id"),
            root_only=params.get("root_only", False),
            limit=params.get("limit", 20),
        )

        return SkillResponse(
            success=True,
            message=f"Found {len(goals)} goals",
            data=[g.to_dict() for g in goals],
            skill_name=self.name,
            tool_name="goal_list",
        )

    async def _get_goal(self, params: Dict[str, Any]) -> SkillResponse:
        """Get a specific goal."""
        goal = await self._goal_manager.get_goal(params["goal_id"])

        if not goal:
            return SkillResponse(
                success=False,
                message=f"Goal {params['goal_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="goal_get",
            )

        return SkillResponse(
            success=True,
            message=f"Goal: {goal.title}",
            data=goal.to_dict(),
            skill_name=self.name,
            tool_name="goal_get",
        )

    async def _complete_goal(self, params: Dict[str, Any]) -> SkillResponse:
        """Mark goal as completed."""
        from gathering.agents.goals import GoalStatus
        from datetime import timezone

        goal = await self._goal_manager.update_goal(
            params["goal_id"],
            status=GoalStatus.COMPLETED,
            progress_percent=100,
            result_summary=params["result_summary"],
            lessons_learned=params.get("lessons_learned"),
            artifacts=params.get("artifacts", []),
            completed_at=datetime.now(timezone.utc),
        )

        if not goal:
            return SkillResponse(
                success=False,
                message=f"Goal {params['goal_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="goal_complete",
            )

        return SkillResponse(
            success=True,
            message=f"Goal completed: {goal.title}",
            data=goal.to_dict(),
            skill_name=self.name,
            tool_name="goal_complete",
        )

    async def _fail_goal(self, params: Dict[str, Any]) -> SkillResponse:
        """Mark goal as failed."""
        from gathering.agents.goals import GoalStatus
        from datetime import timezone

        goal = await self._goal_manager.update_goal(
            params["goal_id"],
            status=GoalStatus.FAILED,
            status_message=params["reason"],
            lessons_learned=params.get("lessons_learned"),
            completed_at=datetime.now(timezone.utc),
        )

        if not goal:
            return SkillResponse(
                success=False,
                message=f"Goal {params['goal_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="goal_fail",
            )

        return SkillResponse(
            success=True,
            message=f"Goal marked as failed: {goal.title}",
            data=goal.to_dict(),
            skill_name=self.name,
            tool_name="goal_fail",
        )

    async def _add_subgoal(self, params: Dict[str, Any]) -> SkillResponse:
        """Add a subgoal to a parent goal."""
        parent = await self._goal_manager.get_goal(params["parent_id"])
        if not parent:
            return SkillResponse(
                success=False,
                message=f"Parent goal {params['parent_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="goal_add_subgoal",
            )

        # Use parent's agent if not specified
        agent_id = params.get("agent_id", parent.agent_id)

        goal = await self._goal_manager.create_goal(
            agent_id=agent_id,
            title=params["title"],
            description=params["description"],
            parent_id=parent.id,
            depth=parent.depth + 1,
        )

        # Mark parent as decomposed
        await self._goal_manager.update_goal(
            parent.id,
            is_decomposed=True,
        )

        return SkillResponse(
            success=True,
            message=f"Subgoal created: {goal.title} (under {parent.title})",
            data=goal.to_dict(),
            skill_name=self.name,
            tool_name="goal_add_subgoal",
        )
