"""
Agent Session - Tracks agent state for session resume.
Enables agents to pick up where they left off after compaction or new sessions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone


@dataclass
class AgentSession:
    """
    Session tracking for an agent.

    Stores everything needed to resume a session:
    - Recent messages (sliding window)
    - Current working state
    - Resume summary
    """

    id: Optional[int] = None
    agent_id: int = 0
    project_id: Optional[int] = None

    # Timestamps
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Session state
    status: str = "active"  # "active", "paused", "completed"

    # Resume information
    resume_summary: str = ""  # Auto-generated summary of current state
    last_message: str = ""  # Last user message
    last_response: str = ""  # Last agent response

    # Recent message history (sliding window for context)
    recent_messages: List[Dict[str, Any]] = field(default_factory=list)
    max_messages: int = 20  # Keep last N messages

    # Working context
    working_files: List[str] = field(default_factory=list)  # Files being modified
    pending_actions: List[str] = field(default_factory=list)  # Actions not yet done
    completed_actions: List[str] = field(default_factory=list)  # Recently completed

    # Current task info
    current_task_id: Optional[int] = None
    current_task_title: str = ""
    current_task_progress: str = ""

    @property
    def needs_resume(self) -> bool:
        """Does this session need a resume summary?"""
        time_since = datetime.now(timezone.utc) - self.last_activity
        return time_since > timedelta(hours=1)

    @property
    def time_since_activity(self) -> timedelta:
        """Time since last activity."""
        return datetime.now(timezone.utc) - self.last_activity

    @property
    def time_since_str(self) -> str:
        """Human-readable time since last activity."""
        delta = self.time_since_activity

        if delta.days > 0:
            return f"{delta.days} jour(s)"

        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours} heure(s)"

        minutes = delta.seconds // 60
        if minutes > 0:
            return f"{minutes} minute(s)"

        return "quelques secondes"

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the session history.

        Args:
            role: "user" or "assistant"
            content: Message content
        """
        self.recent_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Keep only last N messages
        if len(self.recent_messages) > self.max_messages:
            self.recent_messages = self.recent_messages[-self.max_messages:]

        # Update tracking
        self.last_activity = datetime.now(timezone.utc)
        if role == "user":
            self.last_message = content[:500]  # Truncate for storage
        else:
            self.last_response = content[:500]

    def add_working_file(self, file_path: str) -> None:
        """Register a file being worked on."""
        if file_path not in self.working_files:
            self.working_files.append(file_path)

    def remove_working_file(self, file_path: str) -> None:
        """Remove a file from working set."""
        if file_path in self.working_files:
            self.working_files.remove(file_path)

    def add_pending_action(self, action: str) -> None:
        """Add an action to be done."""
        if action not in self.pending_actions:
            self.pending_actions.append(action)

    def complete_action(self, action: str) -> None:
        """Mark an action as completed."""
        if action in self.pending_actions:
            self.pending_actions.remove(action)
        if action not in self.completed_actions:
            self.completed_actions.append(action)
            # Keep only last 10 completed
            if len(self.completed_actions) > 10:
                self.completed_actions = self.completed_actions[-10:]

    def set_current_task(
        self,
        task_id: int,
        title: str,
        progress: str = "",
    ) -> None:
        """Set the current task being worked on."""
        self.current_task_id = task_id
        self.current_task_title = title
        self.current_task_progress = progress

    def clear_current_task(self) -> None:
        """Clear the current task."""
        self.current_task_id = None
        self.current_task_title = ""
        self.current_task_progress = ""

    def generate_resume_summary(self) -> str:
        """
        Generate a summary for session resume.

        Returns:
            Human-readable summary of session state
        """
        lines = []

        # Time context
        lines.append(f"Dernière activité: il y a {self.time_since_str}")

        # Current task
        if self.current_task_id:
            lines.append(f"\nTâche en cours: {self.current_task_title}")
            if self.current_task_progress:
                lines.append(f"Progression: {self.current_task_progress}")

        # Pending actions
        if self.pending_actions:
            lines.append("\nActions en attente:")
            for action in self.pending_actions[:5]:  # Limit to 5
                lines.append(f"  - {action}")

        # Working files
        if self.working_files:
            lines.append("\nFichiers en cours de modification:")
            for f in self.working_files[:5]:
                lines.append(f"  - {f}")

        # Recent completed
        if self.completed_actions:
            lines.append("\nDernières actions complétées:")
            for action in self.completed_actions[-3:]:
                lines.append(f"  - {action}")

        # Last exchange
        if self.last_message:
            lines.append(f"\nDernier message utilisateur: {self.last_message[:100]}...")

        self.resume_summary = "\n".join(lines)
        return self.resume_summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "status": self.status,
            "resume_summary": self.resume_summary,
            "last_message": self.last_message,
            "last_response": self.last_response,
            "recent_messages": self.recent_messages,
            "working_files": self.working_files,
            "pending_actions": self.pending_actions,
            "completed_actions": self.completed_actions,
            "current_task_id": self.current_task_id,
            "current_task_title": self.current_task_title,
            "current_task_progress": self.current_task_progress,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentSession":
        """Create from dictionary."""
        def parse_datetime(val):
            if val is None:
                return datetime.now(timezone.utc)
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(val.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            agent_id=data.get("agent_id", 0),
            project_id=data.get("project_id"),
            started_at=parse_datetime(data.get("started_at")),
            last_activity=parse_datetime(data.get("last_activity")),
            status=data.get("status", "active"),
            resume_summary=data.get("resume_summary", ""),
            last_message=data.get("last_message", ""),
            last_response=data.get("last_response", ""),
            recent_messages=data.get("recent_messages", []),
            working_files=data.get("working_files", []),
            pending_actions=data.get("pending_actions", []),
            completed_actions=data.get("completed_actions", []),
            current_task_id=data.get("current_task_id"),
            current_task_title=data.get("current_task_title", ""),
            current_task_progress=data.get("current_task_progress", ""),
        )


@dataclass
class InjectedContext:
    """
    Context to inject into LLM calls.

    Contains everything the agent needs to respond with full context.
    """

    # Complete system prompt with persona + project + memory
    system_prompt: str = ""

    # Recent message history
    history: List[Dict[str, str]] = field(default_factory=list)

    # Current task info
    current_task: Optional[Dict[str, Any]] = None

    # Relevant memories from RAG
    memories: List[str] = field(default_factory=list)

    # Resume info if session was inactive
    resume_info: Optional[str] = None

    def to_messages(self, user_message: str) -> List[Dict[str, str]]:
        """
        Build complete message list for LLM call.

        Args:
            user_message: The current user message

        Returns:
            List of messages for LLM
        """
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add history
        for msg in self.history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add current message
        messages.append({"role": "user", "content": user_message})

        return messages
