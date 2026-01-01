"""
Circles Skill for GatheRing.

Allows agents to create and participate in collaborative circles.
Circles are groups of agents working together on shared goals.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission

logger = logging.getLogger(__name__)


class CirclesSkill(BaseSkill):
    """
    Skill for managing GatheRing circles.

    Agents can:
    - Create new circles for collaboration
    - Join or leave circles
    - List circles and members
    - Send messages to circle members
    - Assign tasks within circles
    """

    name = "circles"
    description = "Create and manage collaborative agent circles in GatheRing"
    version = "1.0.0"
    required_permissions = [SkillPermission.WRITE]

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
                "name": "circle_create",
                "description": "Create a new collaborative circle for agents to work together.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Circle name"
                        },
                        "description": {
                            "type": "string",
                            "description": "What this circle is about"
                        },
                        "purpose": {
                            "type": "string",
                            "description": "The primary purpose/goal of this circle"
                        },
                        "facilitator_id": {
                            "type": "integer",
                            "description": "Agent ID of the circle facilitator"
                        },
                        "max_members": {
                            "type": "integer",
                            "description": "Maximum number of members",
                            "default": 10
                        },
                        "is_open": {
                            "type": "boolean",
                            "description": "Whether agents can join freely",
                            "default": True
                        }
                    },
                    "required": ["name", "description", "facilitator_id"]
                }
            },
            {
                "name": "circle_list",
                "description": "List available circles.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["active", "paused", "completed", "archived"],
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
                "name": "circle_get",
                "description": "Get details of a specific circle including members.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "circle_id": {
                            "type": "integer",
                            "description": "ID of the circle"
                        }
                    },
                    "required": ["circle_id"]
                }
            },
            {
                "name": "circle_join",
                "description": "Join a circle as a member.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "circle_id": {
                            "type": "integer",
                            "description": "ID of the circle to join"
                        },
                        "agent_id": {
                            "type": "integer",
                            "description": "ID of the agent joining"
                        },
                        "role": {
                            "type": "string",
                            "description": "Role in the circle (member, specialist, observer)",
                            "default": "member"
                        }
                    },
                    "required": ["circle_id", "agent_id"]
                }
            },
            {
                "name": "circle_leave",
                "description": "Leave a circle.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "circle_id": {
                            "type": "integer",
                            "description": "ID of the circle to leave"
                        },
                        "agent_id": {
                            "type": "integer",
                            "description": "ID of the agent leaving"
                        }
                    },
                    "required": ["circle_id", "agent_id"]
                }
            },
            {
                "name": "circle_members",
                "description": "List members of a circle.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "circle_id": {
                            "type": "integer",
                            "description": "ID of the circle"
                        }
                    },
                    "required": ["circle_id"]
                }
            },
            {
                "name": "circle_message",
                "description": "Send a message to circle members.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "circle_id": {
                            "type": "integer",
                            "description": "ID of the circle"
                        },
                        "from_agent_id": {
                            "type": "integer",
                            "description": "ID of the sending agent"
                        },
                        "message": {
                            "type": "string",
                            "description": "Message content"
                        },
                        "message_type": {
                            "type": "string",
                            "enum": ["info", "question", "decision", "update", "request"],
                            "description": "Type of message",
                            "default": "info"
                        }
                    },
                    "required": ["circle_id", "from_agent_id", "message"]
                }
            },
            {
                "name": "circle_update",
                "description": "Update circle status or details.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "circle_id": {
                            "type": "integer",
                            "description": "ID of the circle"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "paused", "completed", "archived"],
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
                    "required": ["circle_id"]
                }
            }
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a circle tool synchronously."""
        self.ensure_initialized()

        try:
            if tool_name == "circle_create":
                return self._create_circle(tool_input)
            elif tool_name == "circle_list":
                return self._list_circles(tool_input)
            elif tool_name == "circle_get":
                return self._get_circle(tool_input)
            elif tool_name == "circle_join":
                return self._join_circle(tool_input)
            elif tool_name == "circle_leave":
                return self._leave_circle(tool_input)
            elif tool_name == "circle_members":
                return self._list_members(tool_input)
            elif tool_name == "circle_message":
                return self._send_message(tool_input)
            elif tool_name == "circle_update":
                return self._update_circle(tool_input)
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

    def _create_circle(self, params: Dict[str, Any]) -> SkillResponse:
        """Create a new circle."""
        result = self._db_service.execute(
            """
            INSERT INTO circle.circles
            (name, description, purpose, facilitator_id, max_members, is_open, status)
            VALUES (%(name)s, %(description)s, %(purpose)s, %(facilitator_id)s,
                    %(max_members)s, %(is_open)s, 'active')
            RETURNING id, name, status, created_at
            """,
            {
                "name": params["name"],
                "description": params["description"],
                "purpose": params.get("purpose", ""),
                "facilitator_id": params["facilitator_id"],
                "max_members": params.get("max_members", 10),
                "is_open": params.get("is_open", True),
            }
        )

        if result:
            circle = result[0]

            # Add facilitator as first member
            self._db_service.execute(
                """
                INSERT INTO circle.circle_members (circle_id, agent_id, role)
                VALUES (%(circle_id)s, %(agent_id)s, 'facilitator')
                """,
                {"circle_id": circle["id"], "agent_id": params["facilitator_id"]}
            )

            return SkillResponse(
                success=True,
                message=f"Circle created: {circle['name']} (ID: {circle['id']})",
                data=self._serialize_row(circle),
                skill_name=self.name,
                tool_name="circle_create",
            )

        return SkillResponse(
            success=False,
            message="Failed to create circle",
            error="creation_failed",
            skill_name=self.name,
            tool_name="circle_create",
        )

    def _list_circles(self, params: Dict[str, Any]) -> SkillResponse:
        """List circles."""
        status = params.get("status")
        limit = params.get("limit", 20)

        if status:
            result = self._db_service.execute(
                """
                SELECT c.id, c.name, c.description, c.status, c.facilitator_id,
                       c.created_at, c.updated_at,
                       COUNT(m.id) as member_count
                FROM circle.circles c
                LEFT JOIN circle.circle_members m ON c.id = m.circle_id
                WHERE c.status = %(status)s
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT %(limit)s
                """,
                {"status": status, "limit": limit}
            )
        else:
            result = self._db_service.execute(
                """
                SELECT c.id, c.name, c.description, c.status, c.facilitator_id,
                       c.created_at, c.updated_at,
                       COUNT(m.id) as member_count
                FROM circle.circles c
                LEFT JOIN circle.circle_members m ON c.id = m.circle_id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT %(limit)s
                """,
                {"limit": limit}
            )

        circles = [self._serialize_row(r) for r in result] if result else []

        return SkillResponse(
            success=True,
            message=f"Found {len(circles)} circles",
            data=circles,
            skill_name=self.name,
            tool_name="circle_list",
        )

    def _get_circle(self, params: Dict[str, Any]) -> SkillResponse:
        """Get a specific circle with members."""
        result = self._db_service.execute(
            """
            SELECT c.*, a.name as facilitator_name
            FROM circle.circles c
            LEFT JOIN agent.agents a ON c.facilitator_id = a.id
            WHERE c.id = %(id)s
            """,
            {"id": params["circle_id"]}
        )

        if not result:
            return SkillResponse(
                success=False,
                message=f"Circle {params['circle_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="circle_get",
            )

        circle = self._serialize_row(result[0])

        # Get members
        members = self._db_service.execute(
            """
            SELECT m.*, a.name as agent_name
            FROM circle.circle_members m
            JOIN agent.agents a ON m.agent_id = a.id
            WHERE m.circle_id = %(circle_id)s
            ORDER BY m.joined_at
            """,
            {"circle_id": params["circle_id"]}
        )
        circle["members"] = [self._serialize_row(m) for m in members] if members else []

        return SkillResponse(
            success=True,
            message=f"Circle: {circle['name']}",
            data=circle,
            skill_name=self.name,
            tool_name="circle_get",
        )

    def _join_circle(self, params: Dict[str, Any]) -> SkillResponse:
        """Join a circle."""
        # Check if circle exists and is open
        circle = self._db_service.execute(
            "SELECT id, name, is_open, max_members FROM circle.circles WHERE id = %(id)s",
            {"id": params["circle_id"]}
        )

        if not circle:
            return SkillResponse(
                success=False,
                message=f"Circle {params['circle_id']} not found",
                error="not_found",
                skill_name=self.name,
                tool_name="circle_join",
            )

        if not circle[0]["is_open"]:
            return SkillResponse(
                success=False,
                message="Circle is not open for new members",
                error="circle_closed",
                skill_name=self.name,
                tool_name="circle_join",
            )

        # Check current member count
        count = self._db_service.execute(
            "SELECT COUNT(*) as cnt FROM circle.circle_members WHERE circle_id = %(id)s",
            {"id": params["circle_id"]}
        )
        if count and count[0]["cnt"] >= circle[0]["max_members"]:
            return SkillResponse(
                success=False,
                message="Circle is at maximum capacity",
                error="circle_full",
                skill_name=self.name,
                tool_name="circle_join",
            )

        # Add member
        try:
            result = self._db_service.execute(
                """
                INSERT INTO circle.circle_members (circle_id, agent_id, role)
                VALUES (%(circle_id)s, %(agent_id)s, %(role)s)
                RETURNING id, circle_id, agent_id, role, joined_at
                """,
                {
                    "circle_id": params["circle_id"],
                    "agent_id": params["agent_id"],
                    "role": params.get("role", "member"),
                }
            )

            return SkillResponse(
                success=True,
                message=f"Joined circle: {circle[0]['name']}",
                data=self._serialize_row(result[0]) if result else {},
                skill_name=self.name,
                tool_name="circle_join",
            )
        except Exception as e:
            if "unique" in str(e).lower():
                return SkillResponse(
                    success=False,
                    message="Already a member of this circle",
                    error="already_member",
                    skill_name=self.name,
                    tool_name="circle_join",
                )
            raise

    def _leave_circle(self, params: Dict[str, Any]) -> SkillResponse:
        """Leave a circle."""
        result = self._db_service.execute(
            """
            DELETE FROM circle.circle_members
            WHERE circle_id = %(circle_id)s AND agent_id = %(agent_id)s
            RETURNING id
            """,
            {
                "circle_id": params["circle_id"],
                "agent_id": params["agent_id"],
            }
        )

        if result:
            return SkillResponse(
                success=True,
                message="Left circle successfully",
                data={"circle_id": params["circle_id"], "agent_id": params["agent_id"]},
                skill_name=self.name,
                tool_name="circle_leave",
            )

        return SkillResponse(
            success=False,
            message="Not a member of this circle",
            error="not_member",
            skill_name=self.name,
            tool_name="circle_leave",
        )

    def _list_members(self, params: Dict[str, Any]) -> SkillResponse:
        """List circle members."""
        result = self._db_service.execute(
            """
            SELECT m.*, a.name as agent_name, a.persona_type
            FROM circle.circle_members m
            JOIN agent.agents a ON m.agent_id = a.id
            WHERE m.circle_id = %(circle_id)s
            ORDER BY m.role, m.joined_at
            """,
            {"circle_id": params["circle_id"]}
        )

        members = [self._serialize_row(m) for m in result] if result else []

        return SkillResponse(
            success=True,
            message=f"Found {len(members)} members",
            data=members,
            skill_name=self.name,
            tool_name="circle_members",
        )

    def _send_message(self, params: Dict[str, Any]) -> SkillResponse:
        """Send a message to circle members."""
        import json

        result = self._db_service.execute(
            """
            INSERT INTO circle.circle_messages
            (circle_id, from_agent_id, message_type, content)
            VALUES (%(circle_id)s, %(from_agent_id)s, %(message_type)s, %(content)s)
            RETURNING id, circle_id, message_type, created_at
            """,
            {
                "circle_id": params["circle_id"],
                "from_agent_id": params["from_agent_id"],
                "message_type": params.get("message_type", "info"),
                "content": params["message"],
            }
        )

        if result:
            return SkillResponse(
                success=True,
                message="Message sent to circle",
                data=self._serialize_row(result[0]),
                skill_name=self.name,
                tool_name="circle_message",
            )

        return SkillResponse(
            success=False,
            message="Failed to send message",
            error="send_failed",
            skill_name=self.name,
            tool_name="circle_message",
        )

    def _update_circle(self, params: Dict[str, Any]) -> SkillResponse:
        """Update a circle."""
        updates = []
        values = {"id": params["circle_id"]}

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
                tool_name="circle_update",
            )

        updates.append("updated_at = CURRENT_TIMESTAMP")

        result = self._db_service.execute(
            f"""
            UPDATE circle.circles
            SET {', '.join(updates)}
            WHERE id = %(id)s
            RETURNING id, name, status, updated_at
            """,
            values
        )

        if result:
            return SkillResponse(
                success=True,
                message=f"Circle updated: {result[0]['name']}",
                data=self._serialize_row(result[0]),
                skill_name=self.name,
                tool_name="circle_update",
            )

        return SkillResponse(
            success=False,
            message=f"Circle {params['circle_id']} not found",
            error="not_found",
            skill_name=self.name,
            tool_name="circle_update",
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
