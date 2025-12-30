"""
Orchestration module for GatheRing framework.
Implements the Gathering Circle - a hybrid orchestration model for multi-agent collaboration.

The Gathering Circle is based on these principles:
- **Autonomy**: Each agent decides its own actions, can refuse tasks
- **Facilitator ≠ Manager**: Routes tasks, doesn't command
- **Event-driven communication**: Pub/sub for loose coupling
- **Peer review**: Work is reviewed by another agent before completion
- **Human as arbiter**: Escalations go to the human

Components:
- EventBus: Central pub/sub for agent communication
- Facilitator: Routes tasks to agents, detects conflicts
- GatheringCircle: Main orchestrator that ties everything together

Usage:
    from gathering.orchestration import GatheringCircle, AgentHandle

    # Create the circle
    circle = GatheringCircle(name="my-team", require_review=True)

    # Add agents
    circle.add_agent(AgentHandle(
        id=1,
        name="Claude",
        provider="anthropic",
        model="claude-3-opus",
        competencies=["architecture", "python", "review"],
        can_review=["code", "architecture"],
    ))

    circle.add_agent(AgentHandle(
        id=2,
        name="DeepSeek",
        provider="deepseek",
        model="deepseek-coder",
        competencies=["python", "testing", "optimization"],
        can_review=["code"],
    ))

    # Start the circle
    await circle.start()

    # Create a task - facilitator will route it
    task_id = await circle.create_task(
        title="Implement user authentication",
        description="Add JWT-based authentication to the API",
        required_competencies=["python", "security"],
    )

    # Agents work autonomously...
    # When done, they submit work and it goes through review

    # Handle escalations
    @circle.on_escalation
    async def handle_escalation(data):
        print(f"Human intervention needed: {data['reason']}")
"""

from gathering.orchestration.events import (
    Event,
    EventBus,
    EventType,
    EventFilter,
    AgentEventMixin,
    # Convenience functions
    task_created_event,
    task_completed_event,
    review_requested_event,
    mention_event,
    conflict_detected_event,
)

from gathering.orchestration.facilitator import (
    Facilitator,
    Conflict,
    ConflictType,
    TaskOffer,
    AgentMetrics,
)

from gathering.orchestration.circle import (
    GatheringCircle,
    AgentHandle,
    CircleTask,
    CircleStatus,
)

from gathering.orchestration.background import (
    BackgroundTask,
    BackgroundTaskStatus,
    BackgroundTaskRunner,
    BackgroundTaskExecutor,
    TaskStep,
    get_background_executor,
)

from gathering.orchestration.scheduler import (
    Scheduler,
    ScheduledAction,
    ScheduledActionRun,
    ScheduleType,
    ScheduledActionStatus,
    get_scheduler,
)

__all__ = [
    # Main orchestrator
    "GatheringCircle",
    "AgentHandle",
    "CircleTask",
    "CircleStatus",
    # Facilitator
    "Facilitator",
    "Conflict",
    "ConflictType",
    "TaskOffer",
    "AgentMetrics",
    # Events
    "Event",
    "EventBus",
    "EventType",
    "EventFilter",
    "AgentEventMixin",
    # Event helpers
    "task_created_event",
    "task_completed_event",
    "review_requested_event",
    "mention_event",
    "conflict_detected_event",
    # Background tasks
    "BackgroundTask",
    "BackgroundTaskStatus",
    "BackgroundTaskRunner",
    "BackgroundTaskExecutor",
    "TaskStep",
    "get_background_executor",
    # Scheduler
    "Scheduler",
    "ScheduledAction",
    "ScheduledActionRun",
    "ScheduleType",
    "ScheduledActionStatus",
    "get_scheduler",
]
