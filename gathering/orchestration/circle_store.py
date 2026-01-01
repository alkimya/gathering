"""
CircleStore - PostgreSQL persistence for GatheringCircles.

Handles storage and retrieval of circles, members, tasks, and collaboration state.
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

# Import pycopg (local PostgreSQL wrapper)
from pycopg import Database, Config

# Import event bus
from gathering.events import event_bus, Event, EventType


class CircleStore:
    """
    PostgreSQL storage for Gathering Circles.

    Persists circle state, members, tasks, and events.

    Example:
        store = CircleStore.from_env()

        # Create circle
        circle_id = store.create_circle(
            name="dev-team",
            display_name="Development Team",
            auto_route=True,
            require_review=True,
        )

        # Add members
        store.add_member(circle_id, agent_id=1, competencies=["python"])

        # Create task
        task_id = store.create_task(
            circle_id=circle_id,
            title="Implement feature",
            required_competencies=["python"],
        )
    """

    def __init__(self, db: Database):
        self.db = db

    def _publish_event(self, event: Event) -> None:
        """
        Publish an event to the event bus (sync wrapper).

        Since CircleStore uses sync methods but event_bus is async,
        we need to run the async publish in a new event loop if needed.
        """
        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule the task
                asyncio.create_task(event_bus.publish(event))
            else:
                # Otherwise run it directly
                loop.run_until_complete(event_bus.publish(event))
        except RuntimeError:
            # No event loop, create one
            asyncio.run(event_bus.publish(event))

    @classmethod
    def from_env(cls, dotenv_path: Optional[str] = None) -> "CircleStore":
        """Create CircleStore from environment variables."""
        if dotenv_path:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path)

        config = Config(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'gathering'),
            user=os.getenv('DB_USER', 'loc'),
            password=os.getenv('DB_PASSWORD', ''),
        )
        db = Database(config)
        return cls(db)

    # =========================================================================
    # CIRCLE OPERATIONS
    # =========================================================================

    def create_circle(
        self,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        owner_id: Optional[str] = None,
        project_id: Optional[int] = None,
        auto_route: bool = True,
        require_review: bool = True,
        settings: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Create a new circle.

        Args:
            name: Unique circle name
            display_name: Human-readable name
            description: Circle description
            owner_id: Owner user ID
            project_id: Optional project ID to link circle to project
            auto_route: Enable automatic task routing
            require_review: Require review for tasks
            settings: Additional settings (JSON)

        Returns:
            Circle ID
        """
        result = self.db.execute("""
            INSERT INTO circle.circles (
                name, display_name, description, owner_id, project_id,
                auto_route, require_review, settings, status
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s::jsonb, 'stopped'::circle_status
            )
            RETURNING id
        """, [
            name, display_name or name, description, owner_id, project_id,
            auto_route, require_review, json.dumps(settings or {}),
        ])
        circle_id = result[0]["id"]

        # Publish circle created event
        self._publish_event(Event(
            type=EventType.CIRCLE_CREATED,
            data={
                "circle_id": circle_id,
                "name": name,
                "display_name": display_name or name,
                "project_id": project_id,
            },
            circle_id=circle_id,
            project_id=project_id,
        ))

        return circle_id

    def get_circle(self, circle_id: int) -> Optional[Dict[str, Any]]:
        """Get circle by ID."""
        result = self.db.execute("""
            SELECT *
            FROM circle.circles
            WHERE id = %s
        """, [circle_id])
        return result[0] if result else None

    def list_circles(
        self,
        is_active: Optional[bool] = None,
        status: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List circles with optional filters."""
        conditions = []
        params = []

        if is_active is not None:
            conditions.append("is_active = %s")
            params.append(is_active)

        if status:
            conditions.append("status = %s::circle_status")
            params.append(status)

        if project_id is not None:
            conditions.append("project_id = %s")
            params.append(project_id)

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        result = self.db.execute(f"""
            SELECT *
            FROM circle.circles
            WHERE {where_clause}
            ORDER BY created_at DESC
        """, params)
        return list(result)

    def update_circle_status(
        self,
        circle_id: int,
        status: str,
    ) -> bool:
        """Update circle status."""
        timestamp_field = None
        if status == "running":
            timestamp_field = "started_at"
        elif status == "stopped":
            timestamp_field = "stopped_at"

        if timestamp_field:
            self.db.execute(f"""
                UPDATE circle.circles
                SET status = %s::circle_status,
                    {timestamp_field} = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, [status, circle_id])
        else:
            self.db.execute("""
                UPDATE circle.circles
                SET status = %s::circle_status,
                    updated_at = NOW()
                WHERE id = %s
            """, [status, circle_id])

        return True

    def delete_circle(self, circle_id: int) -> bool:
        """Soft delete circle."""
        self.db.execute("""
            UPDATE circle.circles
            SET is_active = FALSE,
                status = 'stopped'::circle_status,
                stopped_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, [circle_id])
        return True

    # =========================================================================
    # MEMBER OPERATIONS
    # =========================================================================

    def add_member(
        self,
        circle_id: int,
        agent_id: int,
        role: str = "member",
        competencies: Optional[List[str]] = None,
        can_review: Optional[List[str]] = None,
    ) -> int:
        """Add agent to circle."""
        result = self.db.execute("""
            INSERT INTO circle.members (
                circle_id, agent_id, role, competencies, can_review, is_active
            ) VALUES (
                %s, %s, %s::agent_role, %s, %s, TRUE
            )
            ON CONFLICT (circle_id, agent_id)
            DO UPDATE SET
                is_active = TRUE,
                role = EXCLUDED.role,
                competencies = EXCLUDED.competencies,
                can_review = EXCLUDED.can_review
            RETURNING id
        """, [circle_id, agent_id, role, competencies or [], can_review or []])
        member_id = result[0]["id"]

        # Publish member added event
        self._publish_event(Event(
            type=EventType.CIRCLE_MEMBER_ADDED,
            data={
                "member_id": member_id,
                "circle_id": circle_id,
                "agent_id": agent_id,
                "role": role,
                "competencies": competencies or [],
            },
            source_agent_id=agent_id,
            circle_id=circle_id,
        ))

        return member_id

    def remove_member(self, circle_id: int, agent_id: int) -> bool:
        """Remove agent from circle (soft delete)."""
        self.db.execute("""
            UPDATE circle.members
            SET is_active = FALSE,
                left_at = NOW()
            WHERE circle_id = %s AND agent_id = %s
        """, [circle_id, agent_id])
        return True

    def list_members(
        self,
        circle_id: int,
        is_active: bool = True,
    ) -> List[Dict[str, Any]]:
        """List circle members."""
        result = self.db.execute("""
            SELECT m.*, a.name as agent_name
            FROM circle.members m
            JOIN agent.agents a ON a.id = m.agent_id
            WHERE m.circle_id = %s AND m.is_active = %s
            ORDER BY m.joined_at
        """, [circle_id, is_active])
        return list(result)

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    def create_task(
        self,
        circle_id: int,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        task_type: str = "feature",
        priority: str = "medium",
        required_competencies: Optional[List[str]] = None,
        requires_review: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Create a task in the circle.

        Args:
            circle_id: Circle ID
            title: Task title
            description: Task description
            project_id: Optional project ID (inherits from circle if not provided)
            task_type: Type of task (feature, bug, docs, etc.)
            priority: Task priority (low, medium, high, critical)
            required_competencies: Required skills for this task
            requires_review: Whether task requires review
            context: Additional context (JSON)

        Returns:
            Task ID
        """
        result = self.db.execute("""
            INSERT INTO circle.tasks (
                circle_id, project_id, title, description, task_type, priority,
                required_competencies, requires_review, status, context
            ) VALUES (
                %s, %s, %s, %s, %s, %s::task_priority,
                %s, %s, 'pending'::task_status, %s::jsonb
            )
            RETURNING id
        """, [
            circle_id, project_id, title, description, task_type, priority,
            required_competencies or [], requires_review, json.dumps(context or {}),
        ])
        task_id = result[0]["id"]

        # Publish task created event
        self._publish_event(Event(
            type=EventType.TASK_CREATED,
            data={
                "task_id": task_id,
                "circle_id": circle_id,
                "title": title,
                "priority": priority,
                "required_competencies": required_competencies or [],
            },
            circle_id=circle_id,
            project_id=project_id,
        ))

        return task_id

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        result = self.db.execute("""
            SELECT *
            FROM circle.tasks
            WHERE id = %s
        """, [task_id])
        return result[0] if result else None

    def list_tasks(
        self,
        circle_id: int,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List tasks in circle."""
        if status:
            result = self.db.execute("""
                SELECT *
                FROM circle.tasks
                WHERE circle_id = %s AND status = %s::task_status
                ORDER BY priority DESC, created_at
            """, [circle_id, status])
        else:
            result = self.db.execute("""
                SELECT *
                FROM circle.tasks
                WHERE circle_id = %s
                ORDER BY priority DESC, created_at
            """, [circle_id])
        return list(result)

    def update_task_status(
        self,
        task_id: int,
        status: str,
        assigned_agent_id: Optional[int] = None,
        result: Optional[str] = None,
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update task status."""
        timestamp_updates = []
        if status == "in_progress" and not self.get_task(task_id).get("started_at"):
            timestamp_updates.append("started_at = NOW()")
        elif status in ("completed", "failed"):
            timestamp_updates.append("completed_at = NOW()")

        timestamp_sql = ", ".join(timestamp_updates) + "," if timestamp_updates else ""

        artifacts_json = json.dumps(artifacts) if artifacts else None

        # Get task before update to get circle_id
        task = self.get_task(task_id)

        self.db.execute(f"""
            UPDATE circle.tasks
            SET status = %s::task_status,
                assigned_agent_id = COALESCE(%s, assigned_agent_id),
                result = COALESCE(%s, result),
                artifacts = COALESCE(%s::jsonb, artifacts),
                {timestamp_sql}
                updated_at = NOW()
            WHERE id = %s
        """, [status, assigned_agent_id, result, artifacts_json, task_id])

        # Publish appropriate event based on status
        if task:
            event_type_map = {
                "in_progress": EventType.TASK_STARTED,
                "completed": EventType.TASK_COMPLETED,
                "failed": EventType.TASK_FAILED,
            }

            event_type = event_type_map.get(status, EventType.TASK_ASSIGNED if assigned_agent_id else None)

            if event_type:
                self._publish_event(Event(
                    type=event_type,
                    data={
                        "task_id": task_id,
                        "circle_id": task.get("circle_id"),
                        "status": status,
                        "assigned_agent_id": assigned_agent_id,
                        "result": result,
                    },
                    source_agent_id=assigned_agent_id,
                    circle_id=task.get("circle_id"),
                    project_id=task.get("project_id"),
                ))

        return True

    # =========================================================================
    # EVENTS
    # =========================================================================

    def log_event(
        self,
        circle_id: int,
        event_type: str,
        data: Dict[str, Any],
        agent_id: Optional[int] = None,
    ) -> int:
        """Log an event for the circle."""
        result = self.db.execute("""
            INSERT INTO circle.events (
                circle_id, event_type, agent_id, event_data
            ) VALUES (
                %s, %s, %s, %s::jsonb
            )
            RETURNING id
        """, [circle_id, event_type, agent_id, json.dumps(data)])
        return result[0]["id"]

    def get_events(
        self,
        circle_id: int,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent events for circle."""
        if event_type:
            result = self.db.execute("""
                SELECT *
                FROM circle.events
                WHERE circle_id = %s AND event_type = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, [circle_id, event_type, limit])
        else:
            result = self.db.execute("""
                SELECT *
                FROM circle.events
                WHERE circle_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, [circle_id, limit])
        return list(result)

    def close(self):
        """Close database connection."""
        self.db.close()
