"""
Memory Service - Manages context injection for agents.
Provides relevant context from persona, project, session, and long-term memory.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol
from datetime import datetime, timezone
import hashlib

from gathering.agents.persona import AgentPersona
from gathering.agents.project_context import ProjectContext
from gathering.agents.session import AgentSession, InjectedContext
from gathering.utils.bounded_lru import BoundedLRUDict


class MemoryStore(Protocol):
    """Protocol for memory storage backends."""

    async def store_memory(
        self,
        agent_id: int,
        content: str,
        memory_type: str,
        metadata: Dict[str, Any],
    ) -> int:
        """Store a memory and return its ID."""
        ...

    async def search_memories(
        self,
        agent_id: int,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search memories by semantic similarity."""
        ...

    async def get_recent_memories(
        self,
        agent_id: int,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get most recent memories."""
        ...


@dataclass
class MemoryEntry:
    """A single memory entry."""

    id: Optional[int] = None
    agent_id: int = 0
    content: str = ""
    memory_type: str = "general"  # "conversation", "learning", "decision", "error"
    importance: float = 0.5  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def content_hash(self) -> str:
        """Hash of content for deduplication."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


class InMemoryStore:
    """Simple in-memory implementation of MemoryStore for testing."""

    def __init__(self):
        self._memories: Dict[int, List[MemoryEntry]] = {}  # agent_id -> memories
        self._next_id = 1

    async def store_memory(
        self,
        agent_id: int,
        content: str,
        memory_type: str,
        metadata: Dict[str, Any],
    ) -> int:
        """Store a memory in memory."""
        if agent_id not in self._memories:
            self._memories[agent_id] = []

        entry = MemoryEntry(
            id=self._next_id,
            agent_id=agent_id,
            content=content,
            memory_type=memory_type,
            metadata=metadata,
        )
        self._next_id += 1
        self._memories[agent_id].append(entry)
        return entry.id

    async def search_memories(
        self,
        agent_id: int,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Simple keyword search (real impl would use embeddings).

        Searches for any word from the query in the memory content.
        Scores results by number of matching words.
        """
        if agent_id not in self._memories:
            return []

        # Extract significant words (>2 chars, excluding common stop words)
        stop_words = {"que", "sur", "est", "les", "des", "une", "son", "ses", "qui", "pour", "dans", "avec"}
        query_words = [
            w.lower() for w in query.split()
            if len(w) > 2 and w.lower() not in stop_words
        ]

        if not query_words:
            return []

        scored_results = []
        for entry in self._memories[agent_id]:
            if memory_types and entry.memory_type not in memory_types:
                continue

            content_lower = entry.content.lower()
            # Count matching words
            matches = sum(1 for word in query_words if word in content_lower)

            if matches > 0:
                scored_results.append((matches, {
                    "id": entry.id,
                    "content": entry.content,
                    "type": entry.memory_type,
                    "metadata": entry.metadata,
                    "created_at": entry.created_at.isoformat(),
                }))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in scored_results[:limit]]

    async def get_recent_memories(
        self,
        agent_id: int,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get most recent memories."""
        if agent_id not in self._memories:
            return []

        memories = self._memories[agent_id]
        if memory_types:
            memories = [m for m in memories if m.memory_type in memory_types]

        # Sort by created_at descending
        memories = sorted(memories, key=lambda m: m.created_at, reverse=True)

        return [
            {
                "id": m.id,
                "content": m.content,
                "type": m.memory_type,
                "metadata": m.metadata,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories[:limit]
        ]


class MemoryService:
    """
    Service that manages context injection for agents.

    Responsibilities:
    - Build complete context before each LLM call
    - Retrieve relevant memories via RAG
    - Track what to remember from conversations
    - Generate session resume summaries
    """

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
    ):
        """
        Initialize the memory service.

        Args:
            store: Storage backend for memories (defaults to in-memory)
            embedding_fn: Function to generate embeddings for RAG
        """
        self.store = store or InMemoryStore()
        self.embedding_fn = embedding_fn

        # Cache for frequently accessed data (bounded to prevent memory exhaustion)
        self._persona_cache: BoundedLRUDict = BoundedLRUDict(max_size=500)
        self._project_cache: BoundedLRUDict = BoundedLRUDict(max_size=100)
        self._session_cache: BoundedLRUDict = BoundedLRUDict(max_size=500)

    def set_persona(self, agent_id: int, persona: AgentPersona) -> None:
        """Cache a persona for an agent."""
        self._persona_cache[agent_id] = persona

    def get_persona(self, agent_id: int) -> Optional[AgentPersona]:
        """Get cached persona for an agent."""
        return self._persona_cache.get(agent_id)

    def set_project(self, project_id: int, project: ProjectContext) -> None:
        """Cache a project context."""
        self._project_cache[project_id] = project

    def get_project(self, project_id: int) -> Optional[ProjectContext]:
        """Get cached project context."""
        return self._project_cache.get(project_id)

    def get_or_create_session(
        self,
        agent_id: int,
        project_id: Optional[int] = None,
    ) -> AgentSession:
        """Get existing session or create a new one."""
        if agent_id not in self._session_cache:
            self._session_cache[agent_id] = AgentSession(
                agent_id=agent_id,
                project_id=project_id,
            )
        return self._session_cache[agent_id]

    def get_session(self, agent_id: int) -> Optional[AgentSession]:
        """Get session for an agent."""
        return self._session_cache.get(agent_id)

    async def build_context(
        self,
        agent_id: int,
        user_message: str,
        project_id: Optional[int] = None,
        include_memories: bool = True,
        memory_limit: int = 5,
    ) -> InjectedContext:
        """
        Build complete context for an LLM call.

        This is the main entry point - call this before each LLM request.

        Args:
            agent_id: The agent making the request
            user_message: The current user message
            project_id: Optional project context to include
            include_memories: Whether to retrieve relevant memories
            memory_limit: Max memories to include

        Returns:
            InjectedContext ready to be converted to LLM messages
        """
        context = InjectedContext()

        # 1. Build system prompt from persona
        persona = self._persona_cache.get(agent_id)
        project = self._project_cache.get(project_id) if project_id else None

        if persona:
            context.system_prompt = persona.build_system_prompt(project)
        elif project:
            context.system_prompt = f"## Contexte Projet\n{project.to_prompt()}"

        # 2. Get session and history
        session = self.get_or_create_session(agent_id, project_id)

        # Check if resume is needed
        if session.needs_resume:
            context.resume_info = session.generate_resume_summary()

        # Add recent history
        context.history = session.recent_messages.copy()

        # 3. Get current task info
        if session.current_task_id:
            context.current_task = {
                "id": session.current_task_id,
                "title": session.current_task_title,
                "progress": session.current_task_progress,
            }

        # 4. Retrieve relevant memories via RAG
        if include_memories and user_message:
            memories = await self.store.search_memories(
                agent_id=agent_id,
                query=user_message,
                limit=memory_limit,
            )
            context.memories = [m["content"] for m in memories]

        return context

    async def record_exchange(
        self,
        agent_id: int,
        user_message: str,
        assistant_response: str,
        should_remember: bool = False,
        memory_type: str = "conversation",
        importance: float = 0.5,
    ) -> None:
        """
        Record a conversation exchange.

        Args:
            agent_id: The agent involved
            user_message: What the user said
            assistant_response: What the agent responded
            should_remember: Whether to store as long-term memory
            memory_type: Type of memory if storing
            importance: Importance score if storing
        """
        session = self.get_or_create_session(agent_id)

        # Add to session history
        session.add_message("user", user_message)
        session.add_message("assistant", assistant_response)

        # Store as long-term memory if requested
        if should_remember:
            await self.store.store_memory(
                agent_id=agent_id,
                content=f"User: {user_message}\nAssistant: {assistant_response}",
                memory_type=memory_type,
                metadata={"importance": importance},
            )

    async def remember(
        self,
        agent_id: int,
        content: str,
        memory_type: str = "learning",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Store a specific piece of information as memory.

        Args:
            agent_id: The agent to remember for
            content: What to remember
            memory_type: Type of memory
            metadata: Additional metadata

        Returns:
            Memory ID
        """
        return await self.store.store_memory(
            agent_id=agent_id,
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
        )

    async def recall(
        self,
        agent_id: int,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[str]:
        """
        Recall relevant memories.

        Args:
            agent_id: The agent recalling
            query: What to search for
            memory_types: Filter by types
            limit: Max results

        Returns:
            List of memory contents
        """
        memories = await self.store.search_memories(
            agent_id=agent_id,
            query=query,
            memory_types=memory_types,
            limit=limit,
        )
        return [m["content"] for m in memories]

    def track_file(self, agent_id: int, file_path: str) -> None:
        """Track a file being worked on."""
        session = self.get_or_create_session(agent_id)
        session.add_working_file(file_path)

    def untrack_file(self, agent_id: int, file_path: str) -> None:
        """Stop tracking a file."""
        session = self.get_or_create_session(agent_id)
        session.remove_working_file(file_path)

    def add_pending_action(self, agent_id: int, action: str) -> None:
        """Add an action to be done."""
        session = self.get_or_create_session(agent_id)
        session.add_pending_action(action)

    def complete_action(self, agent_id: int, action: str) -> None:
        """Mark an action as completed."""
        session = self.get_or_create_session(agent_id)
        session.complete_action(action)

    def set_current_task(
        self,
        agent_id: int,
        task_id: int,
        title: str,
        progress: str = "",
    ) -> None:
        """Set the current task for an agent."""
        session = self.get_or_create_session(agent_id)
        session.set_current_task(task_id, title, progress)

    def clear_current_task(self, agent_id: int) -> None:
        """Clear the current task."""
        session = self.get_or_create_session(agent_id)
        session.clear_current_task()

    def get_resume_summary(self, agent_id: int) -> Optional[str]:
        """Get resume summary for an agent if needed."""
        session = self._session_cache.get(agent_id)
        if session and session.needs_resume:
            return session.generate_resume_summary()
        return None

    def export_session(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """Export session data for persistence."""
        session = self._session_cache.get(agent_id)
        if session:
            return session.to_dict()
        return None

    def import_session(self, agent_id: int, data: Dict[str, Any]) -> AgentSession:
        """Import session data from persistence."""
        session = AgentSession.from_dict(data)
        self._session_cache[agent_id] = session
        return session


# Convenience function for quick context building
async def build_agent_context(
    agent_id: int,
    user_message: str,
    persona: Optional[AgentPersona] = None,
    project: Optional[ProjectContext] = None,
    session: Optional[AgentSession] = None,
    memories: Optional[List[str]] = None,
) -> InjectedContext:
    """
    Quick helper to build context without a full MemoryService.

    Args:
        agent_id: Agent ID
        user_message: Current user message
        persona: Optional persona
        project: Optional project context
        session: Optional session
        memories: Optional list of relevant memories

    Returns:
        InjectedContext ready for LLM
    """
    context = InjectedContext()

    # Build system prompt
    if persona:
        context.system_prompt = persona.build_system_prompt(project)
    elif project:
        context.system_prompt = f"## Contexte Projet\n{project.to_prompt()}"

    # Add session info
    if session:
        context.history = session.recent_messages.copy()
        if session.needs_resume:
            context.resume_info = session.generate_resume_summary()
        if session.current_task_id:
            context.current_task = {
                "id": session.current_task_id,
                "title": session.current_task_title,
                "progress": session.current_task_progress,
            }

    # Add memories
    if memories:
        context.memories = memories

    return context
