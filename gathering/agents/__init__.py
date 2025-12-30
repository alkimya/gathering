"""
Agents module for GatheRing framework.
Contains agent implementations, personas, memory, and session management.

Key Components:
- AgentWrapper: Main abstraction that wraps an LLM with persona and memory
- AgentPersona: Persistent identity for agents
- ProjectContext: Project-specific context (venv, tools, conventions)
- AgentSession: Session tracking for resume capability
- MemoryService: Context injection and memory management

Usage:
    from gathering.agents import (
        AgentWrapper,
        AgentPersona,
        ProjectContext,
        MemoryService,
        ARCHITECT_PERSONA,
        create_architect_agent,
    )

    # Create an agent with full persistence
    agent = AgentWrapper(
        agent_id=1,
        persona=ARCHITECT_PERSONA,
        llm=my_llm_provider,
    )
    agent.set_project(ProjectContext.from_path("/path/to/project"))

    # Chat with context injection
    response = await agent.chat("Implémente la feature X")
"""

# Legacy interfaces (from core)
from gathering.core.interfaces import IAgent, IPersonalityBlock, ICompetency
from gathering.core.implementations import BasicAgent, BasicPersonalityBlock

# New persistence components
from gathering.agents.persona import (
    AgentPersona,
    ARCHITECT_PERSONA,
    SENIOR_DEV_PERSONA,
    CODE_SPECIALIST_PERSONA,
    QA_PERSONA,
)

from gathering.agents.project_context import (
    ProjectContext,
    GATHERING_PROJECT,
)

from gathering.agents.session import (
    AgentSession,
    InjectedContext,
)

from gathering.agents.memory import (
    MemoryService,
    MemoryStore,
    MemoryEntry,
    InMemoryStore,
    build_agent_context,
)

from gathering.agents.wrapper import (
    AgentWrapper,
    AgentConfig,
    AgentResponse,
    LLMProvider,
    Skill,
    create_architect_agent,
    create_developer_agent,
    create_code_specialist_agent,
)

from gathering.agents.resume import (
    ResumeContext,
    ResumeStrategy,
    SessionResumeManager,
    SessionPersistence,
    InMemorySessionPersistence,
    create_resume_prompt,
)

from gathering.agents.conversation import (
    AgentConversation,
    ConversationMessage,
    ConversationResult,
    ConversationStatus,
    TurnStrategy,
    CollaborativeTask,
    AgentParticipant,
    AgentWrapperParticipant,
    create_agent_conversation,
)

__all__ = [
    # Legacy
    "IAgent",
    "IPersonalityBlock",
    "ICompetency",
    "BasicAgent",
    "BasicPersonalityBlock",
    # Persona
    "AgentPersona",
    "ARCHITECT_PERSONA",
    "SENIOR_DEV_PERSONA",
    "CODE_SPECIALIST_PERSONA",
    "QA_PERSONA",
    # Project Context
    "ProjectContext",
    "GATHERING_PROJECT",
    # Session
    "AgentSession",
    "InjectedContext",
    # Memory
    "MemoryService",
    "MemoryStore",
    "MemoryEntry",
    "InMemoryStore",
    "build_agent_context",
    # Wrapper
    "AgentWrapper",
    "AgentConfig",
    "AgentResponse",
    "LLMProvider",
    "Skill",
    # Factory functions
    "create_architect_agent",
    "create_developer_agent",
    "create_code_specialist_agent",
    # Resume
    "ResumeContext",
    "ResumeStrategy",
    "SessionResumeManager",
    "SessionPersistence",
    "InMemorySessionPersistence",
    "create_resume_prompt",
    # Conversation
    "AgentConversation",
    "ConversationMessage",
    "ConversationResult",
    "ConversationStatus",
    "TurnStrategy",
    "CollaborativeTask",
    "AgentParticipant",
    "AgentWrapperParticipant",
    "create_agent_conversation",
]
