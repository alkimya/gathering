"""
Agent Goal Management for GatheRing.
Enables long-term goal tracking with hierarchical decomposition.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from gathering.orchestration.events import EventBus, EventType

logger = logging.getLogger(__name__)


class GoalStatus(Enum):
    """Status of a goal."""
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalPriority(Enum):
    """Priority level of a goal."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Goal:
    """Represents an agent goal."""
    id: int
    agent_id: int
    title: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    priority: GoalPriority = GoalPriority.MEDIUM
    progress_percent: int = 0

    # Hierarchy
    parent_id: Optional[int] = None
    depth: int = 0

    # Optional fields
    circle_id: Optional[int] = None
    success_criteria: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    status_message: Optional[str] = None

    # Timing
    deadline: Optional[datetime] = None
    estimated_hours: Optional[Decimal] = None
    actual_hours: Decimal = Decimal("0")

    # Decomposition
    is_decomposed: bool = False
    decomposition_strategy: Optional[str] = None
    max_subgoals: int = 5

    # Execution
    background_task_id: Optional[int] = None
    last_worked_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3

    # Results
    result_summary: Optional[str] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    lessons_learned: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_by: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Computed fields (from dashboard view)
    agent_name: Optional[str] = None
    subgoal_count: int = 0
    completed_subgoals: int = 0
    blocking_count: int = 0

    def is_blocked(self) -> bool:
        """Check if goal is blocked by dependencies."""
        return self.blocking_count > 0

    def can_start(self) -> bool:
        """Check if goal can be started."""
        return (
            self.status == GoalStatus.PENDING and
            not self.is_blocked() and
            self.attempts < self.max_attempts
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "circle_id": self.circle_id,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "title": self.title,
            "description": self.description,
            "success_criteria": self.success_criteria,
            "status": self.status.value,
            "priority": self.priority.value,
            "progress_percent": self.progress_percent,
            "status_message": self.status_message,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "estimated_hours": float(self.estimated_hours) if self.estimated_hours else None,
            "actual_hours": float(self.actual_hours),
            "is_decomposed": self.is_decomposed,
            "decomposition_strategy": self.decomposition_strategy,
            "background_task_id": self.background_task_id,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "result_summary": self.result_summary,
            "artifacts": self.artifacts,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "agent_name": self.agent_name,
            "subgoal_count": self.subgoal_count,
            "completed_subgoals": self.completed_subgoals,
            "blocking_count": self.blocking_count,
        }


@dataclass
class GoalDependency:
    """Represents a dependency between goals."""
    id: int
    goal_id: int
    depends_on_id: int
    dependency_type: str = "blocks"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GoalActivity:
    """Activity log entry for a goal."""
    id: int
    goal_id: int
    activity_type: str
    description: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    actor_type: Optional[str] = None
    actor_id: Optional[int] = None
    tokens_used: int = 0
    duration_ms: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GoalManager:
    """
    Manages agent goals with decomposition and progress tracking.

    Features:
    - Hierarchical goal structure (goals with subgoals)
    - Automatic decomposition via LLM
    - Progress tracking from subgoals
    - Dependency management
    - Background task integration
    """

    def __init__(
        self,
        db_service: Any = None,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize the goal manager.

        Args:
            db_service: Database service for persistence
            event_bus: Event bus for publishing events
        """
        self.db_service = db_service
        self.event_bus = event_bus or EventBus()

    def _row_to_goal(self, row) -> Goal:
        """Convert database row to Goal."""
        return Goal(
            id=row["id"],
            agent_id=row["agent_id"],
            circle_id=row.get("circle_id"),
            parent_id=row.get("parent_id"),
            depth=row.get("depth", 0),
            title=row["title"],
            description=row["description"],
            success_criteria=row.get("success_criteria"),
            context=row.get("context", {}),
            status=GoalStatus(row["status"]),
            priority=GoalPriority(row["priority"]),
            progress_percent=row.get("progress_percent", 0),
            status_message=row.get("status_message"),
            deadline=row.get("deadline"),
            estimated_hours=row.get("estimated_hours"),
            actual_hours=row.get("actual_hours", Decimal("0")),
            is_decomposed=row.get("is_decomposed", False),
            decomposition_strategy=row.get("decomposition_strategy"),
            max_subgoals=row.get("max_subgoals", 5),
            background_task_id=row.get("background_task_id"),
            last_worked_at=row.get("last_worked_at"),
            attempts=row.get("attempts", 0),
            max_attempts=row.get("max_attempts", 3),
            result_summary=row.get("result_summary"),
            artifacts=row.get("artifacts", []),
            lessons_learned=row.get("lessons_learned"),
            tags=row.get("tags", []),
            metadata=row.get("metadata", {}),
            created_by=row.get("created_by"),
            created_at=row.get("created_at", datetime.now(timezone.utc)),
            updated_at=row.get("updated_at", datetime.now(timezone.utc)),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            agent_name=row.get("agent_name"),
            subgoal_count=row.get("subgoal_count", 0),
            completed_subgoals=row.get("completed_subgoals", 0),
            blocking_count=row.get("blocking_count", 0),
        )

    # CRUD Operations

    async def create_goal(self, goal: Goal) -> int:
        """Create a new goal."""
        import json
        if not self.db_service:
            raise ValueError("Database service not configured")

        row = self.db_service.execute_one("""
            INSERT INTO agent.goals
            (agent_id, circle_id, parent_id, depth, title, description,
             success_criteria, context, status, priority, deadline,
             estimated_hours, decomposition_strategy, max_subgoals,
             tags, metadata, created_by)
            VALUES (%(agent_id)s, %(circle_id)s, %(parent_id)s, %(depth)s, %(title)s, %(description)s,
                    %(success_criteria)s, %(context)s, %(status)s, %(priority)s, %(deadline)s,
                    %(estimated_hours)s, %(decomposition_strategy)s, %(max_subgoals)s,
                    %(tags)s, %(metadata)s, %(created_by)s)
            RETURNING id
        """, {
            'agent_id': goal.agent_id,
            'circle_id': goal.circle_id,
            'parent_id': goal.parent_id,
            'depth': goal.depth,
            'title': goal.title,
            'description': goal.description,
            'success_criteria': goal.success_criteria,
            'context': json.dumps(goal.context) if goal.context else '{}',
            'status': goal.status.value,
            'priority': goal.priority.value,
            'deadline': goal.deadline,
            'estimated_hours': float(goal.estimated_hours) if goal.estimated_hours else None,
            'decomposition_strategy': goal.decomposition_strategy,
            'max_subgoals': goal.max_subgoals,
            'tags': goal.tags,
            'metadata': json.dumps(goal.metadata) if goal.metadata else '{}',
            'created_by': goal.created_by,
        })

        goal_id = row["id"]

        await self.event_bus.emit(EventType.TASK_CREATED, {
            "goal_id": goal_id,
            "agent_id": goal.agent_id,
            "title": goal.title,
            "priority": goal.priority.value,
        })

        logger.info(f"Created goal {goal_id}: {goal.title}")
        return goal_id

    async def get_goal(self, goal_id: int) -> Optional[Goal]:
        """Get a goal by ID."""
        if not self.db_service:
            return None

        row = self.db_service.execute_one(
            "SELECT * FROM public.goals_dashboard WHERE id = %(id)s",
            {'id': goal_id},
        )

        if not row:
            return None

        return self._row_to_goal(row)

    async def update_goal(self, goal_id: int, updates: Dict[str, Any]) -> bool:
        """Update a goal."""
        if not self.db_service or not updates:
            return False

        # Build dynamic update query with named params
        set_clauses = []
        params = {'id': goal_id}
        for key, value in updates.items():
            # Handle enum values
            if key == "status" and isinstance(value, GoalStatus):
                value = value.value
            elif key == "priority" and isinstance(value, GoalPriority):
                value = value.value
            set_clauses.append(f"{key} = %({key})s")
            params[key] = value

        self.db_service.execute(f"""
            UPDATE agent.goals
            SET {', '.join(set_clauses)}
            WHERE id = %(id)s
        """, params)

        return True

    async def delete_goal(self, goal_id: int) -> bool:
        """Delete a goal and its subgoals."""
        if not self.db_service:
            return False

        self.db_service.execute(
            "DELETE FROM agent.goals WHERE id = %(id)s",
            {'id': goal_id},
        )

        return True

    async def list_goals(
        self,
        agent_id: Optional[int] = None,
        circle_id: Optional[int] = None,
        status: Optional[GoalStatus] = None,
        parent_id: Optional[int] = None,
        root_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Goal]:
        """List goals with optional filters."""
        if not self.db_service:
            return []

        query = "SELECT * FROM public.goals_dashboard WHERE 1=1"
        params: Dict[str, Any] = {'limit': limit, 'offset': offset}

        if agent_id:
            query += " AND agent_id = %(agent_id)s"
            params['agent_id'] = agent_id

        if circle_id:
            query += " AND circle_id = %(circle_id)s"
            params['circle_id'] = circle_id

        if status:
            query += " AND status = %(status)s"
            params['status'] = status.value

        if parent_id is not None:
            query += " AND parent_id = %(parent_id)s"
            params['parent_id'] = parent_id

        if root_only:
            query += " AND parent_id IS NULL"

        query += " ORDER BY priority DESC, created_at DESC"
        query += " LIMIT %(limit)s OFFSET %(offset)s"

        rows = self.db_service.execute(query, params)

        return [self._row_to_goal(row) for row in rows]

    # Status Management

    async def start_goal(self, goal_id: int) -> bool:
        """Start working on a goal."""
        goal = await self.get_goal(goal_id)
        if not goal or not goal.can_start():
            return False

        return await self.update_goal(goal_id, {
            "status": GoalStatus.ACTIVE,
            "started_at": datetime.now(timezone.utc),
            "attempts": goal.attempts + 1,
            "last_worked_at": datetime.now(timezone.utc),
        })

    async def complete_goal(
        self,
        goal_id: int,
        result_summary: Optional[str] = None,
        artifacts: Optional[List[Dict]] = None,
    ) -> bool:
        """Mark a goal as completed."""
        updates: Dict[str, Any] = {
            "status": GoalStatus.COMPLETED,
            "progress_percent": 100,
            "completed_at": datetime.now(timezone.utc),
        }
        if result_summary:
            updates["result_summary"] = result_summary
        if artifacts:
            updates["artifacts"] = artifacts

        success = await self.update_goal(goal_id, updates)

        if success:
            await self.event_bus.emit(EventType.TASK_COMPLETED, {
                "goal_id": goal_id,
                "result": result_summary,
            })

        return success

    async def fail_goal(
        self,
        goal_id: int,
        reason: str,
        lessons_learned: Optional[str] = None,
    ) -> bool:
        """Mark a goal as failed."""
        updates: Dict[str, Any] = {
            "status": GoalStatus.FAILED,
            "status_message": reason,
            "completed_at": datetime.now(timezone.utc),
        }
        if lessons_learned:
            updates["lessons_learned"] = lessons_learned

        return await self.update_goal(goal_id, updates)

    async def pause_goal(self, goal_id: int, reason: Optional[str] = None) -> bool:
        """Pause a goal."""
        updates: Dict[str, Any] = {"status": GoalStatus.PAUSED}
        if reason:
            updates["status_message"] = reason
        return await self.update_goal(goal_id, updates)

    async def resume_goal(self, goal_id: int) -> bool:
        """Resume a paused goal."""
        return await self.update_goal(goal_id, {
            "status": GoalStatus.ACTIVE,
            "status_message": None,
        })

    async def update_progress(self, goal_id: int, percent: int, message: Optional[str] = None) -> bool:
        """Update goal progress."""
        updates: Dict[str, Any] = {"progress_percent": min(100, max(0, percent))}
        if message:
            updates["status_message"] = message
        return await self.update_goal(goal_id, updates)

    # Decomposition

    async def decompose_goal(
        self,
        goal_id: int,
        agent: Any,  # AgentWrapper
        max_subgoals: int = 5,
    ) -> List[int]:
        """
        Decompose a goal into subgoals using the agent.

        Args:
            goal_id: Goal to decompose
            agent: Agent to use for decomposition
            max_subgoals: Maximum number of subgoals to create

        Returns:
            List of created subgoal IDs
        """
        goal = await self.get_goal(goal_id)
        if not goal:
            return []

        # Build decomposition prompt
        prompt = f"""
Decompose this goal into {max_subgoals} or fewer specific, actionable subgoals.

Goal: {goal.title}
Description: {goal.description}
{f"Success Criteria: {goal.success_criteria}" if goal.success_criteria else ""}

For each subgoal, provide:
1. A clear, specific title (max 100 chars)
2. A detailed description of what needs to be done
3. Success criteria - how do we know it's complete?
4. Estimated time in hours (if applicable)

Format your response as a numbered list with clear sections for each subgoal.
Focus on actionable, measurable outcomes.
"""

        # Get decomposition from agent
        response = await agent.generate(prompt)

        # Parse response and create subgoals
        subgoal_ids = []
        subgoals = self._parse_decomposition_response(response, goal)

        for i, subgoal_data in enumerate(subgoals[:max_subgoals]):
            subgoal = Goal(
                id=0,
                agent_id=goal.agent_id,
                circle_id=goal.circle_id,
                parent_id=goal_id,
                depth=goal.depth + 1,
                title=subgoal_data.get("title", f"Subgoal {i+1}"),
                description=subgoal_data.get("description", ""),
                success_criteria=subgoal_data.get("success_criteria"),
                estimated_hours=subgoal_data.get("estimated_hours"),
                priority=goal.priority,
                created_by="agent",
            )

            subgoal_id = await self.create_goal(subgoal)
            subgoal_ids.append(subgoal_id)

        # Mark parent as decomposed
        await self.update_goal(goal_id, {
            "is_decomposed": True,
            "decomposition_strategy": "auto",
        })

        # Log activity
        await self._log_activity(goal_id, "decomposed", f"Created {len(subgoal_ids)} subgoals")

        return subgoal_ids

    def _parse_decomposition_response(self, response: str, parent: Goal) -> List[Dict]:
        """Parse LLM response into subgoal data."""
        # Simple parsing - in production, use more robust parsing
        subgoals = []
        current_subgoal: Dict[str, Any] = {}

        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                if current_subgoal:
                    subgoals.append(current_subgoal)
                    current_subgoal = {}
                continue

            # Check for numbered items (1., 2., etc.)
            if line and line[0].isdigit() and "." in line[:3]:
                if current_subgoal:
                    subgoals.append(current_subgoal)
                current_subgoal = {"title": line.split(".", 1)[-1].strip()[:100]}

            # Check for labeled fields
            lower_line = line.lower()
            if "title:" in lower_line:
                current_subgoal["title"] = line.split(":", 1)[-1].strip()[:100]
            elif "description:" in lower_line:
                current_subgoal["description"] = line.split(":", 1)[-1].strip()
            elif "success" in lower_line and ":" in line:
                current_subgoal["success_criteria"] = line.split(":", 1)[-1].strip()
            elif "time:" in lower_line or "hours:" in lower_line or "estimated:" in lower_line:
                try:
                    hours_str = "".join(c for c in line.split(":", 1)[-1] if c.isdigit() or c == ".")
                    if hours_str:
                        current_subgoal["estimated_hours"] = Decimal(hours_str)
                except Exception:
                    pass

        if current_subgoal:
            subgoals.append(current_subgoal)

        return subgoals

    # Dependencies

    async def add_dependency(
        self,
        goal_id: int,
        depends_on_id: int,
        dependency_type: str = "blocks",
    ) -> bool:
        """Add a dependency between goals."""
        if not self.db_service:
            return False

        try:
            self.db_service.execute("""
                INSERT INTO agent.goal_dependencies (goal_id, depends_on_id, dependency_type)
                VALUES (%(goal_id)s, %(depends_on_id)s, %(dependency_type)s)
                ON CONFLICT DO NOTHING
            """, {'goal_id': goal_id, 'depends_on_id': depends_on_id, 'dependency_type': dependency_type})
            return True
        except Exception as e:
            logger.error(f"Failed to add dependency: {e}")
            return False

    async def remove_dependency(self, goal_id: int, depends_on_id: int) -> bool:
        """Remove a dependency."""
        if not self.db_service:
            return False

        self.db_service.execute("""
            DELETE FROM agent.goal_dependencies
            WHERE goal_id = %(goal_id)s AND depends_on_id = %(depends_on_id)s
        """, {'goal_id': goal_id, 'depends_on_id': depends_on_id})

        return True

    async def get_dependencies(self, goal_id: int) -> List[Goal]:
        """Get goals that this goal depends on."""
        if not self.db_service:
            return []

        rows = self.db_service.execute("""
            SELECT g.* FROM public.goals_dashboard g
            JOIN agent.goal_dependencies gd ON g.id = gd.depends_on_id
            WHERE gd.goal_id = %(goal_id)s
        """, {'goal_id': goal_id})

        return [self._row_to_goal(row) for row in rows]

    async def get_dependents(self, goal_id: int) -> List[Goal]:
        """Get goals that depend on this goal."""
        if not self.db_service:
            return []

        rows = self.db_service.execute("""
            SELECT g.* FROM public.goals_dashboard g
            JOIN agent.goal_dependencies gd ON g.id = gd.goal_id
            WHERE gd.depends_on_id = %(goal_id)s
        """, {'goal_id': goal_id})

        return [self._row_to_goal(row) for row in rows]

    # Activities

    async def _log_activity(
        self,
        goal_id: int,
        activity_type: str,
        description: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        actor_type: str = "system",
        actor_id: Optional[int] = None,
    ) -> None:
        """Log an activity for a goal."""
        if not self.db_service:
            return

        self.db_service.execute("""
            INSERT INTO agent.goal_activities
            (goal_id, activity_type, description, old_value, new_value, actor_type, actor_id)
            VALUES (%(goal_id)s, %(activity_type)s, %(description)s, %(old_value)s, %(new_value)s, %(actor_type)s, %(actor_id)s)
        """, {
            'goal_id': goal_id,
            'activity_type': activity_type,
            'description': description,
            'old_value': old_value,
            'new_value': new_value,
            'actor_type': actor_type,
            'actor_id': actor_id,
        })

    async def get_activities(
        self,
        goal_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[GoalActivity]:
        """Get activity log for a goal."""
        if not self.db_service:
            return []

        rows = self.db_service.execute("""
            SELECT * FROM agent.goal_activities
            WHERE goal_id = %(goal_id)s
            ORDER BY created_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """, {'goal_id': goal_id, 'limit': limit, 'offset': offset})

        return [
            GoalActivity(
                id=row["id"],
                goal_id=row["goal_id"],
                activity_type=row["activity_type"],
                description=row.get("description"),
                old_value=row.get("old_value"),
                new_value=row.get("new_value"),
                actor_type=row.get("actor_type"),
                actor_id=row.get("actor_id"),
                tokens_used=row.get("tokens_used", 0),
                duration_ms=row.get("duration_ms", 0),
                created_at=row.get("created_at", datetime.now(timezone.utc)),
            )
            for row in rows
        ]

    # Subgoals

    async def get_subgoals(self, goal_id: int) -> List[Goal]:
        """Get direct subgoals of a goal."""
        return await self.list_goals(parent_id=goal_id)

    async def get_goal_tree(self, goal_id: int) -> Dict[str, Any]:
        """Get full goal tree including all nested subgoals."""
        goal = await self.get_goal(goal_id)
        if not goal:
            return {}

        subgoals = await self.get_subgoals(goal_id)

        result = goal.to_dict()
        result["subgoals"] = []

        for subgoal in subgoals:
            subtree = await self.get_goal_tree(subgoal.id)
            result["subgoals"].append(subtree)

        return result


# Singleton instance
_goal_manager: Optional[GoalManager] = None


def get_goal_manager(
    db_service: Any = None,
    event_bus: Optional[EventBus] = None,
) -> GoalManager:
    """Get the global goal manager instance."""
    global _goal_manager
    if _goal_manager is None:
        _goal_manager = GoalManager(
            db_service=db_service,
            event_bus=event_bus,
        )
    return _goal_manager
