"""
Session Resume - Handles session restoration after compaction or new sessions.
Enables agents to pick up where they left off with full context.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol
from datetime import datetime, timezone, timedelta
from enum import Enum

from gathering.agents.session import AgentSession
from gathering.agents.project_context import ProjectContext


class ResumeStrategy(Enum):
    """Strategies for session resume."""

    FULL = "full"  # Include everything
    SUMMARY = "summary"  # Condensed summary only
    TASK_FOCUSED = "task_focused"  # Focus on current task
    MINIMAL = "minimal"  # Just essential context


@dataclass
class ResumeContext:
    """
    Context for resuming a session.

    Contains all the information needed to restore an agent's state
    after context window compaction or a new session.
    """

    # Time information
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    time_away: timedelta = field(default_factory=timedelta)

    # Session summary
    summary: str = ""

    # Current work state
    current_task: Optional[Dict[str, Any]] = None
    working_files: List[str] = field(default_factory=list)
    pending_actions: List[str] = field(default_factory=list)
    completed_actions: List[str] = field(default_factory=list)

    # Last conversation
    last_user_message: str = ""
    last_agent_response: str = ""

    # Project context (condensed)
    project_notes: List[str] = field(default_factory=list)

    def to_prompt(self, strategy: ResumeStrategy = ResumeStrategy.FULL) -> str:
        """
        Generate a resume prompt based on strategy.

        Args:
            strategy: How much detail to include

        Returns:
            Resume prompt for injection
        """
        if strategy == ResumeStrategy.MINIMAL:
            return self._minimal_prompt()
        elif strategy == ResumeStrategy.SUMMARY:
            return self._summary_prompt()
        elif strategy == ResumeStrategy.TASK_FOCUSED:
            return self._task_focused_prompt()
        else:
            return self._full_prompt()

    def _time_away_str(self) -> str:
        """Human-readable time away."""
        if self.time_away.days > 0:
            return f"{self.time_away.days} jour(s)"
        hours = self.time_away.seconds // 3600
        if hours > 0:
            return f"{hours} heure(s)"
        minutes = self.time_away.seconds // 60
        if minutes > 0:
            return f"{minutes} minute(s)"
        return "quelques secondes"

    def _minimal_prompt(self) -> str:
        """Minimal resume - just essentials."""
        lines = [
            "## Reprise de Session",
            f"Dernière activité: il y a {self._time_away_str()}",
        ]

        if self.current_task:
            lines.append(f"Tâche en cours: {self.current_task.get('title', 'N/A')}")

        return "\n".join(lines)

    def _summary_prompt(self) -> str:
        """Summary resume - condensed overview."""
        lines = [
            "## Reprise de Session",
            f"Dernière activité: il y a {self._time_away_str()}",
        ]

        if self.summary:
            lines.append(f"\n{self.summary}")

        return "\n".join(lines)

    def _task_focused_prompt(self) -> str:
        """Task-focused resume - emphasis on current work."""
        lines = [
            "## Reprise de Session",
            f"Dernière activité: il y a {self._time_away_str()}",
        ]

        if self.current_task:
            lines.append(f"\n### Tâche en cours")
            lines.append(f"**{self.current_task.get('title', 'N/A')}**")
            if self.current_task.get('progress'):
                lines.append(f"Progression: {self.current_task['progress']}")

        if self.pending_actions:
            lines.append("\n### Actions en attente")
            for action in self.pending_actions[:5]:
                lines.append(f"- {action}")

        if self.working_files:
            lines.append("\n### Fichiers en cours")
            for f in self.working_files[:5]:
                lines.append(f"- {f}")

        return "\n".join(lines)

    def _full_prompt(self) -> str:
        """Full resume - all details."""
        lines = [
            "## Reprise de Session",
            f"Dernière activité: il y a {self._time_away_str()}",
        ]

        # Current task
        if self.current_task:
            lines.append(f"\n### Tâche en cours")
            lines.append(f"**{self.current_task.get('title', 'N/A')}**")
            if self.current_task.get('progress'):
                lines.append(f"Progression: {self.current_task['progress']}")

        # Pending actions
        if self.pending_actions:
            lines.append("\n### Actions en attente")
            for action in self.pending_actions:
                lines.append(f"- {action}")

        # Working files
        if self.working_files:
            lines.append("\n### Fichiers en cours de modification")
            for f in self.working_files:
                lines.append(f"- {f}")

        # Recently completed
        if self.completed_actions:
            lines.append("\n### Dernières actions complétées")
            for action in self.completed_actions[-5:]:
                lines.append(f"- {action}")

        # Last exchange
        if self.last_user_message:
            lines.append(f"\n### Dernier échange")
            lines.append(f"**Utilisateur**: {self.last_user_message[:200]}...")
            if self.last_agent_response:
                lines.append(f"**Vous**: {self.last_agent_response[:200]}...")

        # Project notes
        if self.project_notes:
            lines.append("\n### Notes projet importantes")
            for note in self.project_notes[:5]:
                lines.append(f"- {note}")

        return "\n".join(lines)


class SessionResumeManager:
    """
    Manages session resume for agents.

    Handles:
    - Detecting when resume is needed
    - Building resume context from session
    - Choosing appropriate resume strategy
    - Generating resume prompts
    """

    def __init__(
        self,
        resume_threshold: timedelta = timedelta(hours=1),
        long_absence_threshold: timedelta = timedelta(hours=24),
    ):
        """
        Initialize the resume manager.

        Args:
            resume_threshold: Time after which resume is needed
            long_absence_threshold: Time after which to use summary strategy
        """
        self.resume_threshold = resume_threshold
        self.long_absence_threshold = long_absence_threshold

    def needs_resume(self, session: AgentSession) -> bool:
        """
        Check if a session needs resume context.

        Args:
            session: The agent session

        Returns:
            True if resume is needed
        """
        time_since = session.time_since_activity
        return time_since > self.resume_threshold

    def get_strategy(self, session: AgentSession) -> ResumeStrategy:
        """
        Determine the best resume strategy based on context.

        Args:
            session: The agent session

        Returns:
            Recommended resume strategy
        """
        time_since = session.time_since_activity

        # Very long absence - use summary
        if time_since > self.long_absence_threshold:
            return ResumeStrategy.SUMMARY

        # Has current task - focus on it
        if session.current_task_id:
            return ResumeStrategy.TASK_FOCUSED

        # Has pending work
        if session.pending_actions or session.working_files:
            return ResumeStrategy.FULL

        # Default to summary
        return ResumeStrategy.SUMMARY

    def build_resume_context(
        self,
        session: AgentSession,
        project: Optional[ProjectContext] = None,
    ) -> ResumeContext:
        """
        Build resume context from a session.

        Args:
            session: The agent session
            project: Optional project context

        Returns:
            ResumeContext ready for prompt generation
        """
        context = ResumeContext(
            last_activity=session.last_activity,
            time_away=session.time_since_activity,
            summary=session.resume_summary or session.generate_resume_summary(),
            working_files=session.working_files.copy(),
            pending_actions=session.pending_actions.copy(),
            completed_actions=session.completed_actions.copy(),
            last_user_message=session.last_message,
            last_agent_response=session.last_response,
        )

        # Add current task if any
        if session.current_task_id:
            context.current_task = {
                "id": session.current_task_id,
                "title": session.current_task_title,
                "progress": session.current_task_progress,
            }

        # Add project notes if available
        if project and project.notes:
            context.project_notes = project.notes.copy()

        return context

    def generate_resume_prompt(
        self,
        session: AgentSession,
        project: Optional[ProjectContext] = None,
        strategy: Optional[ResumeStrategy] = None,
    ) -> str:
        """
        Generate a complete resume prompt.

        Args:
            session: The agent session
            project: Optional project context
            strategy: Optional override for strategy

        Returns:
            Resume prompt string
        """
        if not self.needs_resume(session):
            return ""

        context = self.build_resume_context(session, project)
        actual_strategy = strategy or self.get_strategy(session)

        return context.to_prompt(actual_strategy)


class SessionPersistence(Protocol):
    """Protocol for session persistence backends."""

    async def save_session(self, session: AgentSession) -> None:
        """Save a session to storage."""
        ...

    async def load_session(self, agent_id: int) -> Optional[AgentSession]:
        """Load a session from storage."""
        ...

    async def list_sessions(
        self,
        agent_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[AgentSession]:
        """List sessions with optional filters."""
        ...


class InMemorySessionPersistence:
    """Simple in-memory implementation of SessionPersistence."""

    def __init__(self):
        self._sessions: Dict[int, AgentSession] = {}

    async def save_session(self, session: AgentSession) -> None:
        """Save session to memory."""
        self._sessions[session.agent_id] = session

    async def load_session(self, agent_id: int) -> Optional[AgentSession]:
        """Load session from memory."""
        return self._sessions.get(agent_id)

    async def list_sessions(
        self,
        agent_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[AgentSession]:
        """List all sessions with filters."""
        sessions = list(self._sessions.values())

        if agent_id is not None:
            sessions = [s for s in sessions if s.agent_id == agent_id]

        if status is not None:
            sessions = [s for s in sessions if s.status == status]

        return sessions


# Convenience function
def create_resume_prompt(
    session: AgentSession,
    project: Optional[ProjectContext] = None,
) -> str:
    """
    Quick helper to create a resume prompt.

    Args:
        session: Agent session
        project: Optional project context

    Returns:
        Resume prompt or empty string if not needed
    """
    manager = SessionResumeManager()
    return manager.generate_resume_prompt(session, project)
