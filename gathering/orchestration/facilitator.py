"""
Facilitator for GatheRing orchestration.
Routes tasks to agents, maintains context, detects conflicts.
The Facilitator is NOT a manager - it routes, it doesn't command.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from gathering.orchestration.events import EventBus, EventType, Event

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of conflicts between agents."""
    FILE_COLLISION = "file_collision"       # Two agents modifying same file
    TASK_DEADLOCK = "task_deadlock"         # Circular dependency
    RESOURCE_CONTENTION = "resource"        # Same external resource
    OPINION_DIVERGENCE = "opinion"          # Technical disagreement


@dataclass
class Conflict:
    """A conflict between agents."""
    type: ConflictType
    agent_ids: List[int]
    resource: str
    description: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class TaskOffer:
    """An offer of a task to an agent."""
    task_id: int
    agent_id: int
    offered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    responded: bool = False
    accepted: bool = False
    response_deadline: Optional[datetime] = None


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""
    tasks_completed: int = 0
    tasks_failed: int = 0
    average_quality_score: float = 0.0
    approval_rate: float = 0.0
    current_workload: int = 0
    competency_scores: Dict[str, float] = field(default_factory=dict)

    def calculate_availability_score(self) -> float:
        """Calculate availability score (lower workload = higher score)."""
        # Max 5 concurrent tasks, score decreases as workload increases
        return max(0.0, 1.0 - (self.current_workload / 5.0))


class Facilitator:
    """
    Facilitator for the Gathering Circle.

    The Facilitator routes tasks to the most suitable agents based on:
    - Required competencies
    - Agent workload
    - Historical performance
    - Agent availability

    It does NOT:
    - Make decisions for agents
    - Force agents to accept tasks
    - Override agent autonomy
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._agents: Dict[int, Dict[str, Any]] = {}  # id -> agent info
        self._agent_metrics: Dict[int, AgentMetrics] = {}
        self._pending_offers: Dict[int, TaskOffer] = {}  # task_id -> offer
        self._active_files: Dict[str, int] = {}  # file_path -> agent_id
        self._conflicts: List[Conflict] = []

        # Subscribe to relevant events
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Set up event subscriptions."""

        @self.event_bus.on(EventType.AGENT_JOINED)
        async def on_agent_joined(event: Event):
            await self._handle_agent_joined(event)

        @self.event_bus.on(EventType.AGENT_LEFT)
        async def on_agent_left(event: Event):
            await self._handle_agent_left(event)

        @self.event_bus.on(EventType.TASK_CLAIMED)
        async def on_task_claimed(event: Event):
            await self._handle_task_claimed(event)

        @self.event_bus.on(EventType.TASK_REFUSED)
        async def on_task_refused(event: Event):
            await self._handle_task_refused(event)

        @self.event_bus.on(EventType.TASK_COMPLETED)
        async def on_task_completed(event: Event):
            await self._handle_task_completed(event)

        @self.event_bus.on(EventType.TASK_FAILED)
        async def on_task_failed(event: Event):
            await self._handle_task_failed(event)

        @self.event_bus.on(EventType.REVIEW_COMPLETED)
        async def on_review_completed(event: Event):
            await self._handle_review_completed(event)

    async def _handle_agent_joined(self, event: Event) -> None:
        """Handle agent joining the circle."""
        agent_id = event.data.get("agent_id")
        if agent_id:
            self._agents[agent_id] = {
                "id": agent_id,
                "name": event.data.get("name"),
                "competencies": event.data.get("competencies", []),
                "can_review": event.data.get("can_review", []),
                "joined_at": datetime.now(timezone.utc),
                "is_active": True,
            }
            self._agent_metrics[agent_id] = AgentMetrics(
                competency_scores={
                    comp: 0.8  # Default competency score
                    for comp in event.data.get("competencies", [])
                }
            )
            logger.info(f"Agent {agent_id} joined the circle")

    async def _handle_agent_left(self, event: Event) -> None:
        """Handle agent leaving the circle."""
        agent_id = event.data.get("agent_id")
        if agent_id and agent_id in self._agents:
            self._agents[agent_id]["is_active"] = False
            # Release any files held by this agent
            files_to_release = [
                f for f, a in self._active_files.items() if a == agent_id
            ]
            for f in files_to_release:
                del self._active_files[f]
            logger.info(f"Agent {agent_id} left the circle")

    async def _handle_task_claimed(self, event: Event) -> None:
        """Handle agent claiming a task."""
        task_id = event.data.get("task_id")
        agent_id = event.data.get("agent_id")

        if task_id in self._pending_offers:
            offer = self._pending_offers[task_id]
            offer.responded = True
            offer.accepted = True
            del self._pending_offers[task_id]

        if agent_id in self._agent_metrics:
            self._agent_metrics[agent_id].current_workload += 1

        logger.info(f"Agent {agent_id} claimed task {task_id}")

    async def _handle_task_refused(self, event: Event) -> None:
        """Handle agent refusing a task."""
        task_id = event.data.get("task_id")
        agent_id = event.data.get("agent_id")
        reason = event.data.get("reason", "No reason provided")

        if task_id in self._pending_offers:
            offer = self._pending_offers[task_id]
            offer.responded = True
            offer.accepted = False

        logger.info(f"Agent {agent_id} refused task {task_id}: {reason}")

        # Try to find another agent
        # This would be handled by route_task being called again

    async def _handle_task_completed(self, event: Event) -> None:
        """Handle task completion."""
        agent_id = event.data.get("agent_id")
        artifacts = event.data.get("artifacts", [])

        if agent_id in self._agent_metrics:
            self._agent_metrics[agent_id].tasks_completed += 1
            self._agent_metrics[agent_id].current_workload = max(
                0, self._agent_metrics[agent_id].current_workload - 1
            )

        # Release files
        for artifact in artifacts:
            if artifact in self._active_files:
                del self._active_files[artifact]

    async def _handle_task_failed(self, event: Event) -> None:
        """Handle task failure."""
        agent_id = event.data.get("agent_id")

        if agent_id in self._agent_metrics:
            self._agent_metrics[agent_id].tasks_failed += 1
            self._agent_metrics[agent_id].current_workload = max(
                0, self._agent_metrics[agent_id].current_workload - 1
            )

    async def _handle_review_completed(self, event: Event) -> None:
        """Handle review completion - update agent metrics."""
        author_id = event.data.get("author_id")
        score = event.data.get("score", 0)
        approved = event.data.get("status") == "approved"

        if author_id in self._agent_metrics:
            metrics = self._agent_metrics[author_id]

            # Update average quality score (running average)
            total_tasks = metrics.tasks_completed
            if total_tasks > 0:
                metrics.average_quality_score = (
                    (metrics.average_quality_score * (total_tasks - 1) + score)
                    / total_tasks
                )

            # Update approval rate
            if approved:
                total_reviews = metrics.tasks_completed
                approvals = metrics.approval_rate * (total_reviews - 1)
                metrics.approval_rate = (approvals + 1) / total_reviews

    def register_agent(
        self,
        agent_id: int,
        name: str,
        competencies: List[str],
        can_review: Optional[List[str]] = None,
    ) -> None:
        """
        Register an agent with the facilitator.

        Args:
            agent_id: Unique agent ID
            name: Agent name
            competencies: List of competency tags
            can_review: Review types this agent can perform
        """
        self._agents[agent_id] = {
            "id": agent_id,
            "name": name,
            "competencies": competencies,
            "can_review": can_review or [],
            "joined_at": datetime.now(timezone.utc),
            "is_active": True,
        }
        self._agent_metrics[agent_id] = AgentMetrics(
            competency_scores={comp: 0.8 for comp in competencies}
        )

    def unregister_agent(self, agent_id: int) -> None:
        """Unregister an agent."""
        if agent_id in self._agents:
            self._agents[agent_id]["is_active"] = False

    async def route_task(
        self,
        task_id: int,
        title: str,
        required_competencies: List[str],
        priority: int = 5,
        excluded_agents: Optional[List[int]] = None,
    ) -> Optional[int]:
        """
        Route a task to the best available agent.

        Args:
            task_id: Task ID
            title: Task title
            required_competencies: Required competencies
            priority: Task priority (1-10, lower = higher)
            excluded_agents: Agents to exclude (e.g., for review routing)

        Returns:
            Agent ID if task was offered, None if no suitable agent
        """
        excluded = set(excluded_agents or [])

        # Find candidate agents
        candidates = self._find_candidates(required_competencies, excluded)

        if not candidates:
            logger.warning(
                f"No suitable agent found for task {task_id} "
                f"requiring {required_competencies}"
            )
            return None

        # Score and rank candidates
        scored = [
            (agent_id, self._calculate_agent_score(agent_id, required_competencies, priority))
            for agent_id in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Offer to best candidate
        best_agent_id, best_score = scored[0]

        logger.info(
            f"Offering task {task_id} to agent {best_agent_id} "
            f"(score: {best_score:.2f})"
        )

        # Create offer
        offer = TaskOffer(task_id=task_id, agent_id=best_agent_id)
        self._pending_offers[task_id] = offer

        # Emit offer event
        await self.event_bus.emit(
            EventType.TASK_OFFERED,
            {
                "task_id": task_id,
                "title": title,
                "required_competencies": required_competencies,
                "priority": priority,
                "score": best_score,
            },
            target_agent_id=best_agent_id,
        )

        return best_agent_id

    def _find_candidates(
        self,
        required_competencies: List[str],
        excluded: set,
    ) -> List[int]:
        """Find agents that match required competencies."""
        candidates = []

        for agent_id, agent_info in self._agents.items():
            if agent_id in excluded:
                continue
            if not agent_info.get("is_active", False):
                continue

            agent_comps = set(agent_info.get("competencies", []))
            required = set(required_competencies)

            # Agent must have at least some of the required competencies
            if required & agent_comps:  # Intersection not empty
                candidates.append(agent_id)

        return candidates

    def _calculate_agent_score(
        self,
        agent_id: int,
        required_competencies: List[str],
        priority: int,
    ) -> float:
        """
        Calculate suitability score for an agent.

        Score components:
        - Competency match (0-1): How well agent matches requirements
        - Availability (0-1): Based on current workload
        - Quality bonus (0-0.2): Based on historical performance
        - Priority adjustment: Higher priority tasks weighted more

        Returns:
            Score between 0 and ~1.5
        """
        metrics = self._agent_metrics.get(agent_id)
        if not metrics:
            return 0.0

        agent_info = self._agents.get(agent_id, {})
        agent_comps = set(agent_info.get("competencies", []))
        required = set(required_competencies)

        # Competency match score
        if not required:
            competency_score = 1.0
        else:
            matching = len(required & agent_comps)
            competency_score = matching / len(required)

        # Weighted by competency strength
        comp_strength = sum(
            metrics.competency_scores.get(c, 0.5)
            for c in required if c in agent_comps
        )
        if required & agent_comps:
            comp_strength /= len(required & agent_comps)
        else:
            comp_strength = 0.5

        # Availability score
        availability_score = metrics.calculate_availability_score()

        # Quality bonus
        quality_bonus = metrics.approval_rate * 0.2

        # Priority adjustment (higher priority = more weight on competency)
        priority_factor = 1 + (10 - priority) * 0.05

        # Final score
        score = (
            competency_score * comp_strength * 0.5 +
            availability_score * 0.3 +
            quality_bonus
        ) * priority_factor

        return score

    async def route_review(
        self,
        task_id: int,
        author_id: int,
        review_type: str,
        work_summary: str,
    ) -> Optional[int]:
        """
        Route a review request to a suitable agent.

        Args:
            task_id: Task ID being reviewed
            author_id: ID of author (to exclude)
            review_type: Type of review needed
            work_summary: Summary of work to review

        Returns:
            Reviewer agent ID if found
        """
        # Find agents that can do this type of review
        candidates = []

        for agent_id, agent_info in self._agents.items():
            if agent_id == author_id:
                continue  # Author can't review own work
            if not agent_info.get("is_active", False):
                continue

            can_review = agent_info.get("can_review", [])
            if review_type in can_review or "all" in can_review:
                candidates.append(agent_id)

        if not candidates:
            logger.warning(f"No reviewer found for {review_type} review of task {task_id}")
            return None

        # Score reviewers (simpler than task routing)
        scored = []
        for agent_id in candidates:
            metrics = self._agent_metrics.get(agent_id)
            if metrics:
                score = metrics.calculate_availability_score()
                score += metrics.average_quality_score * 0.01  # Quality bonus
            else:
                score = 0.5
            scored.append((agent_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        reviewer_id = scored[0][0]

        # Emit review request event
        await self.event_bus.emit(
            EventType.REVIEW_REQUESTED,
            {
                "task_id": task_id,
                "author_id": author_id,
                "review_type": review_type,
                "work_summary": work_summary,
            },
            target_agent_id=reviewer_id,
        )

        return reviewer_id

    def register_file_access(self, file_path: str, agent_id: int) -> Optional[Conflict]:
        """
        Register an agent accessing a file.
        Detects file collision conflicts.

        Args:
            file_path: Path to file
            agent_id: Agent accessing the file

        Returns:
            Conflict if detected, None otherwise
        """
        if file_path in self._active_files:
            existing_agent = self._active_files[file_path]
            if existing_agent != agent_id:
                conflict = Conflict(
                    type=ConflictType.FILE_COLLISION,
                    agent_ids=[existing_agent, agent_id],
                    resource=file_path,
                    description=f"Both agents want to modify {file_path}",
                )
                self._conflicts.append(conflict)

                # Emit conflict event (try async if loop running)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.event_bus.emit(
                        EventType.CONFLICT_DETECTED,
                        {
                            "conflict_type": conflict.type.value,
                            "agent_ids": conflict.agent_ids,
                            "resource": conflict.resource,
                            "description": conflict.description,
                        }
                    ))
                except RuntimeError:
                    # No event loop running, skip async emit
                    pass

                return conflict

        self._active_files[file_path] = agent_id
        return None

    def release_file(self, file_path: str, agent_id: int) -> None:
        """Release a file after agent is done."""
        if self._active_files.get(file_path) == agent_id:
            del self._active_files[file_path]

    def get_pending_conflicts(self) -> List[Conflict]:
        """Get unresolved conflicts."""
        return [c for c in self._conflicts if not c.resolved]

    def resolve_conflict(self, conflict: Conflict, resolution: str) -> None:
        """Mark a conflict as resolved."""
        conflict.resolved = True
        conflict.resolution = resolution

    def get_agent_metrics(self, agent_id: int) -> Optional[AgentMetrics]:
        """Get metrics for an agent."""
        return self._agent_metrics.get(agent_id)

    def get_all_metrics(self) -> Dict[int, AgentMetrics]:
        """Get metrics for all agents."""
        return dict(self._agent_metrics)

    def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get list of active agents."""
        return [
            info for info in self._agents.values()
            if info.get("is_active", False)
        ]
