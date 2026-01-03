"""
Database models for GatheRing framework.
SQLAlchemy models for PostgreSQL with multi-schema architecture.

Schemas:
    - agent: Agents & Identity
    - circle: Orchestration (Gathering Circles)
    - project: Projects
    - communication: Conversations & Messages
    - memory: Memory & RAG (pgvector)
    - review: Reviews & Quality Control
    - audit: Audit & Logs

Note: Primary keys use BIGINT GENERATED ALWAYS AS IDENTITY (not UUID).
This provides better performance and simpler debugging.
"""

from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Text,
    BigInteger,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
    Identity,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# Try to import pgvector
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    Vector = None
    PGVECTOR_AVAILABLE = False

Base = declarative_base()


# =============================================================================
# Enums
# =============================================================================


class AgentRole(str, Enum):
    """Agent roles within a circle."""
    LEAD = "lead"
    MEMBER = "member"
    SPECIALIST = "specialist"
    REVIEWER = "reviewer"
    OBSERVER = "observer"


class MessageRole(str, Enum):
    """Message author role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    CHANGES_REQUESTED = "changes_requested"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(str, Enum):
    """Review lifecycle states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class ReviewType(str, Enum):
    """Types of review."""
    CODE = "code"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    DOCUMENTATION = "docs"
    QUALITY = "quality"
    FINAL = "final"


class MemoryScope(str, Enum):
    """Memory visibility scope."""
    AGENT = "agent"
    CIRCLE = "circle"
    PROJECT = "project"
    GLOBAL = "global"


class MemoryType(str, Enum):
    """Type of memory entry."""
    FACT = "fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    DECISION = "decision"
    ERROR = "error"
    FEEDBACK = "feedback"
    LEARNING = "learning"


class LogLevel(str, Enum):
    """Audit log severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CircleStatus(str, Enum):
    """Circle status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


class ConversationStatus(str, Enum):
    """Conversation status."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# =============================================================================
# Agent Schema - Agents & Identity
# =============================================================================


class Agent(Base):
    """AI agent with persona and capabilities."""
    __tablename__ = "agents"
    __table_args__ = {"schema": "agent"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    name = Column(String(100), nullable=False)

    # LLM Configuration
    provider = Column(String(50), nullable=False)  # claude, deepseek, openai, ollama
    model = Column(String(100), nullable=False)

    # Personality
    persona = Column(Text)
    traits = Column(ARRAY(String), default=[])
    communication_style = Column(String(50), default="balanced")

    # Competencies and skills
    competencies = Column(ARRAY(String), default=[])
    specializations = Column(ARRAY(String), default=[])
    skill_names = Column(ARRAY(String), default=[])  # Skills available to the agent

    # Review capabilities
    can_review = Column(ARRAY(String), default=[])
    review_strictness = Column(Float, default=0.7)

    # Configuration
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer)

    # Performance metrics
    tasks_completed = Column(Integer, default=0)
    reviews_done = Column(Integer, default=0)
    approval_rate = Column(Float, default=0.0)
    average_quality_score = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default="idle")
    last_active_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    sessions = relationship("Session", back_populates="agent", cascade="all, delete-orphan")
    circle_memberships = relationship("CircleMember", back_populates="agent")
    messages = relationship("Message", back_populates="agent")
    assigned_tasks = relationship("TaskAssignment", back_populates="agent")
    reviews_given = relationship("Review", foreign_keys="Review.reviewer_id", back_populates="reviewer")
    reviews_received = relationship("Review", foreign_keys="Review.author_id", back_populates="author")
    memories = relationship("Memory", back_populates="agent", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Agent #{self.id} {self.name} ({self.provider}/{self.model})>"


class Persona(Base):
    """Reusable persona templates for agents."""
    __tablename__ = "personas"
    __table_args__ = {"schema": "agent"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200))

    # Persona definition
    role = Column(String(100), nullable=False)
    base_prompt = Column(Text, nullable=False)
    traits = Column(ARRAY(String), default=[])
    communication_style = Column(String(50), default="balanced")
    specializations = Column(ARRAY(String), default=[])

    # Default configuration
    default_provider = Column(String(50))
    default_model = Column(String(100))
    default_temperature = Column(Float, default=0.7)

    # Metadata
    description = Column(Text)
    icon = Column(String(50))
    is_builtin = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Session(Base):
    """Agent session with state tracking."""
    __tablename__ = "sessions"
    __table_args__ = {"schema": "agent"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    agent_id = Column(BigInteger, ForeignKey("agent.agents.id"), nullable=False)

    # Session info
    session_token = Column(String(64), unique=True)
    project_id = Column(BigInteger)  # FK added in circle schema

    # Session state
    working_files = Column(ARRAY(String), default=[])
    pending_actions = Column(ARRAY(String), default=[])

    # Current task tracking
    current_task_id = Column(BigInteger)
    current_task_title = Column(String(200))
    current_task_progress = Column(Text)

    # Context window
    context_window_start = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))

    # Resume info
    needs_resume = Column(Boolean, default=False)
    resume_reason = Column(Text)

    # Relationships
    agent = relationship("Agent", back_populates="sessions")


# =============================================================================
# Circle Schema - Orchestration
# =============================================================================


class Circle(Base):
    """Gathering Circle - team of agents working together."""
    __tablename__ = "circles"
    __table_args__ = {"schema": "circle"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200))
    description = Column(Text)

    # Owner
    owner_id = Column(String(100))

    # Project association
    project_id = Column(BigInteger, ForeignKey("project.projects.id"))

    # Circle settings
    settings = Column(JSON, default={})

    # Review policy
    require_review = Column(Boolean, default=True)
    min_reviewers = Column(Integer, default=1)
    auto_assign_reviewer = Column(Boolean, default=True)
    self_review_allowed = Column(Boolean, default=False)
    escalate_on_reject = Column(Boolean, default=True)
    review_policy = Column(JSON, default={})

    # Routing
    auto_route = Column(Boolean, default=True)

    # Status
    status = Column(SQLEnum(CircleStatus), default=CircleStatus.STOPPED)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    stopped_at = Column(DateTime(timezone=True))

    # Relationships
    members = relationship("CircleMember", back_populates="circle", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="circle", cascade="all, delete-orphan")
    conflicts = relationship("Conflict", back_populates="circle", cascade="all, delete-orphan")
    events = relationship("CircleEvent", back_populates="circle", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="circle")

    def __repr__(self):
        return f"<Circle {self.name} status={self.status.value}>"


class CircleMember(Base):
    """Circle membership with roles and permissions."""
    __tablename__ = "members"
    __table_args__ = (
        UniqueConstraint("circle_id", "agent_id", name="uq_circle_agent"),
        {"schema": "circle"},
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"), nullable=False)
    agent_id = Column(BigInteger, ForeignKey("agent.agents.id"), nullable=False)

    # Membership info
    role = Column(SQLEnum(AgentRole), default=AgentRole.MEMBER)
    permissions = Column(JSON, default={})

    # Agent config override for this circle
    competencies = Column(ARRAY(String), default=[])
    can_review = Column(ARRAY(String), default=[])

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True))

    # Relationships
    circle = relationship("Circle", back_populates="members")
    agent = relationship("Agent", back_populates="circle_memberships")


class Task(Base):
    """Task on the shared task board."""
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_priority", "priority"),
        {"schema": "circle"},
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"), nullable=False)
    project_id = Column(BigInteger)  # FK to project.projects

    # Task details
    title = Column(String(200), nullable=False)
    description = Column(Text)
    task_type = Column(String(50), default="general")

    # Priority and status
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)

    # Required competencies
    required_competencies = Column(ARRAY(String), default=[])

    # Review requirement
    requires_review = Column(Boolean, default=True)
    review_types = Column(ARRAY(String), default=["quality"])

    # Context
    context = Column(JSON, default={})

    # Results
    result = Column(Text)
    artifacts = Column(JSON, default=[])
    files_modified = Column(ARRAY(String), default=[])

    # Assignment
    assigned_agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))

    # Relationships
    parent_task_id = Column(BigInteger, ForeignKey("circle.tasks.id"))
    conversation_id = Column(BigInteger)  # FK to communication.conversations

    # Created by
    created_by_agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))
    created_by_user_id = Column(String(100))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    due_at = Column(DateTime(timezone=True))

    # Relationships
    circle = relationship("Circle", back_populates="tasks")
    assignments = relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="task")
    subtasks = relationship("Task", remote_side=[id])

    def __repr__(self):
        return f"<Task #{self.id} {self.title[:30]}>"


class TaskAssignment(Base):
    """Task assignment history."""
    __tablename__ = "task_assignments"
    __table_args__ = (
        UniqueConstraint("task_id", "agent_id", "assignment_role", name="uq_task_agent_role"),
        {"schema": "circle"},
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    task_id = Column(BigInteger, ForeignKey("circle.tasks.id"), nullable=False)
    agent_id = Column(BigInteger, ForeignKey("agent.agents.id"), nullable=False)

    # Assignment type
    assignment_role = Column(String(50), default="assignee")

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    task = relationship("Task", back_populates="assignments")
    agent = relationship("Agent", back_populates="assigned_tasks")


class Conflict(Base):
    """Detected conflicts between agents."""
    __tablename__ = "conflicts"
    __table_args__ = {"schema": "circle"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"), nullable=False)

    # Conflict type
    conflict_type = Column(String(50), nullable=False)

    # Involved parties
    agent_ids = Column(ARRAY(BigInteger), nullable=False)
    task_ids = Column(ARRAY(BigInteger))
    file_paths = Column(ARRAY(String))

    # Conflict details
    description = Column(Text, nullable=False)
    context = Column(JSON, default={})

    # Resolution
    status = Column(String(20), default="open")
    resolution = Column(Text)
    resolved_by_agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))
    resolved_by_user_id = Column(String(100))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))

    # Relationships
    circle = relationship("Circle", back_populates="conflicts")


class CircleEvent(Base):
    """Event log for circle pub/sub system."""
    __tablename__ = "events"
    __table_args__ = {"schema": "circle"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"))

    # Event info
    event_type = Column(String(100), nullable=False)
    source_agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))

    # Event data
    data = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    circle = relationship("Circle", back_populates="events")


# =============================================================================
# Project Schema - Projects
# =============================================================================


class Project(Base):
    """Software project managed by gathering."""
    __tablename__ = "projects"
    __table_args__ = {"schema": "project"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)

    # Basic info
    name = Column(String(200), nullable=False)
    display_name = Column(String(300))
    description = Column(Text)

    # Project location
    repository_url = Column(String(500))
    local_path = Column(String(500))
    branch = Column(String(100), default="main")

    # Project metadata
    tech_stack = Column(ARRAY(String), default=[])
    languages = Column(ARRAY(String), default=[])
    frameworks = Column(ARRAY(String), default=[])

    # Status
    status = Column(String(50), default="active")

    # Context for agents
    context = Column(Text)
    conventions = Column(JSON, default={})
    key_files = Column(JSON, default={})
    commands = Column(JSON, default={})
    notes = Column(ARRAY(String), default=[])

    # Python-specific
    venv_path = Column(String(500))
    python_version = Column(String(20))

    # Quality standards
    quality_standards = Column(JSON, default={
        "code_coverage_min": 80,
        "require_tests": True,
        "require_docs": True,
        "linting_enabled": True,
        "security_scan": True,
    })

    # Tools configuration
    tools = Column(JSON, default={})

    # Owner
    owner_id = Column(String(100))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="project")
    reviews = relationship("Review", back_populates="project")

    def __repr__(self):
        return f"<Project #{self.id} {self.name}>"


class ProjectFile(Base):
    """Indexed project files for RAG search."""
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("project_id", "file_path", name="uq_project_file"),
        {"schema": "project"},
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    project_id = Column(BigInteger, ForeignKey("project.projects.id"), nullable=False)

    # File info
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50))
    file_name = Column(String(200))

    # Content summary
    summary = Column(Text)
    symbols = Column(ARRAY(String), default=[])

    # Vector embedding for RAG
    # embedding = Column(Vector(1536)) if PGVECTOR_AVAILABLE else None

    # File metadata
    size_bytes = Column(Integer)
    line_count = Column(Integer)
    last_modified = Column(DateTime(timezone=True))
    content_hash = Column(String(64))

    # Importance score
    importance = Column(Float, default=0.5)

    # Timestamps
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="files")


# =============================================================================
# Communication Schema - Conversations & Messages
# =============================================================================


class Conversation(Base):
    """Conversation thread between agents."""
    __tablename__ = "conversations"
    __table_args__ = {"schema": "communication"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)

    # Context
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"))
    project_id = Column(BigInteger, ForeignKey("project.projects.id"))
    task_id = Column(BigInteger)  # FK to circle.tasks

    # Conversation metadata
    topic = Column(String(500))
    conversation_type = Column(String(50), default="chat")

    # Participants
    participant_agent_ids = Column(ARRAY(BigInteger), default=[])
    participant_names = Column(ARRAY(String), default=[])

    # Configuration
    max_turns = Column(Integer, default=20)
    turn_strategy = Column(String(50), default="round_robin")
    initial_prompt = Column(Text)

    # Status
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.PENDING)
    turns_taken = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Results
    summary = Column(Text)
    conclusion = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    last_message_at = Column(DateTime(timezone=True))

    # Relationships
    circle = relationship("Circle", back_populates="conversations")
    project = relationship("Project", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class Message(Base):
    """Individual message in a conversation."""
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation", "conversation_id", "created_at"),
        {"schema": "communication"},
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    conversation_id = Column(BigInteger, ForeignKey("communication.conversations.id"), nullable=False)

    # Author
    role = Column(SQLEnum(MessageRole), nullable=False)
    agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))
    agent_name = Column(String(100))
    user_id = Column(String(100))

    # Content
    content = Column(Text, nullable=False)

    # Mentions
    mentions = Column(ARRAY(String), default=[])
    mentioned_agent_ids = Column(ARRAY(BigInteger), default=[])

    # Tool usage
    tool_calls = Column(JSON)
    tool_results = Column(JSON)

    # Metrics
    model_used = Column(String(100))
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    thinking_time_ms = Column(Integer)

    # Threading
    parent_message_id = Column(BigInteger, ForeignKey("communication.messages.id"))
    reply_count = Column(Integer, default=0)

    # Flags
    is_pinned = Column(Boolean, default=False)
    is_sensitive = Column(Boolean, default=False)
    is_broadcast = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    edited_at = Column(DateTime(timezone=True))

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    agent = relationship("Agent", back_populates="messages")
    parent = relationship("Message", remote_side=[id])


class ChatHistory(Base):
    """Direct chat history with agents."""
    __tablename__ = "chat_history"
    __table_args__ = {"schema": "communication"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    agent_id = Column(BigInteger, ForeignKey("agent.agents.id"), nullable=False)
    session_id = Column(BigInteger, ForeignKey("agent.sessions.id"))

    # Message
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # User info
    user_id = Column(String(100))

    # Metrics
    model_used = Column(String(100))
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    agent = relationship("Agent", back_populates="chat_history")


# =============================================================================
# Memory Schema - Memory & RAG
# =============================================================================


class Memory(Base):
    """Long-term memory storage with vector embeddings."""
    __tablename__ = "memories"
    __table_args__ = (
        Index("ix_memories_scope", "scope", "scope_id"),
        Index("ix_memories_key", "key"),
        {"schema": "memory"},
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)

    # Scope
    scope = Column(SQLEnum(MemoryScope), nullable=False)
    scope_id = Column(BigInteger)

    # For agent-scoped memories
    agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))

    # Memory content
    memory_type = Column(SQLEnum(MemoryType), default=MemoryType.FACT)
    key = Column(String(200), nullable=False)
    value = Column(Text, nullable=False)

    # Source
    source_type = Column(String(50))
    source_id = Column(BigInteger)

    # Additional metadata
    tags = Column(ARRAY(String), default=[])
    extra_data = Column(JSON, default={})

    # Vector embedding for semantic search (added dynamically if pgvector available)
    # embedding = Column(Vector(1536)) if PGVECTOR_AVAILABLE else None

    # Importance and recency
    importance = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    relevance_score = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_accessed_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    # Relationships
    agent = relationship("Agent", back_populates="memories")


class KnowledgeBase(Base):
    """Shared knowledge base for RAG retrieval."""
    __tablename__ = "knowledge_base"
    __table_args__ = {"schema": "memory"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)

    # Knowledge item
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100))

    # Scope
    project_id = Column(BigInteger, ForeignKey("project.projects.id"))
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"))
    is_global = Column(Boolean, default=False)

    # Metadata
    tags = Column(ARRAY(String), default=[])
    source_url = Column(String(500))
    author_agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))

    # Quality
    quality_score = Column(Float, default=0.5)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)

    # Status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# =============================================================================
# Review Schema - Reviews & Quality Control
# =============================================================================


class Review(Base):
    """Code review between agents."""
    __tablename__ = "reviews"
    __table_args__ = (
        Index("ix_reviews_task", "task_id"),
        Index("ix_reviews_status", "status"),
        CheckConstraint("author_id != reviewer_id", name="no_self_review"),
        {"schema": "review"},
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)

    # What is being reviewed
    task_id = Column(BigInteger, ForeignKey("circle.tasks.id"), nullable=False)
    project_id = Column(BigInteger, ForeignKey("project.projects.id"))
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"))

    # Who
    author_id = Column(BigInteger, ForeignKey("agent.agents.id"), nullable=False)
    reviewer_id = Column(BigInteger, ForeignKey("agent.agents.id"), nullable=False)

    # Review details
    review_type = Column(SQLEnum(ReviewType), default=ReviewType.QUALITY)
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING)

    # Scores (0-100)
    overall_score = Column(Integer)
    scores = Column(JSON, default={})

    # Feedback
    summary = Column(Text)
    feedback = Column(Text)
    suggestions = Column(JSON, default=[])

    # Issues found
    issues = Column(JSON, default=[])
    blocking_issues_count = Column(Integer, default=0)

    # Changes requested
    changes_requested = Column(JSON, default=[])
    changes_addressed = Column(Boolean, default=False)

    # Review iteration
    iteration = Column(Integer, default=1)
    previous_review_id = Column(BigInteger, ForeignKey("review.reviews.id"))

    # Files reviewed
    files_reviewed = Column(ARRAY(String), default=[])

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    task = relationship("Task", back_populates="reviews")
    project = relationship("Project", back_populates="reviews")
    author = relationship("Agent", foreign_keys=[author_id], back_populates="reviews_received")
    reviewer = relationship("Agent", foreign_keys=[reviewer_id], back_populates="reviews_given")
    previous_review = relationship("Review", remote_side=[id])
    comments = relationship("ReviewComment", back_populates="review", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Review #{self.id} task={self.task_id} status={self.status.value}>"


class ReviewComment(Base):
    """Inline comment on code during review."""
    __tablename__ = "comments"
    __table_args__ = {"schema": "review"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)
    review_id = Column(BigInteger, ForeignKey("review.reviews.id"), nullable=False)

    # Author
    author_id = Column(BigInteger, ForeignKey("agent.agents.id"), nullable=False)

    # Location
    file_path = Column(String(500))
    line_start = Column(Integer)
    line_end = Column(Integer)
    code_snippet = Column(Text)

    # Comment content
    comment = Column(Text, nullable=False)
    severity = Column(String(20), default="suggestion")

    # Code suggestion
    suggested_code = Column(Text)

    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolution_note = Column(Text)
    resolved_by_id = Column(BigInteger, ForeignKey("agent.agents.id"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))

    # Relationships
    review = relationship("Review", back_populates="comments")


class QualityMetric(Base):
    """Historical quality metrics."""
    __tablename__ = "quality_metrics"
    __table_args__ = {"schema": "review"}

    id = Column(BigInteger, Identity(always=True), primary_key=True)

    # Context
    agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))
    project_id = Column(BigInteger, ForeignKey("project.projects.id"))
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"))

    # Metrics
    metric_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20))

    # Additional data
    metric_data = Column(JSON, default={})

    # Time period
    period_type = Column(String(20), default="daily")
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))

    # Timestamps
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


# =============================================================================
# Audit Schema - Audit & Logs
# =============================================================================


class AuditLog(Base):
    """Comprehensive audit log."""
    __tablename__ = "logs"
    __table_args__ = (
        Index("ix_logs_timestamp", "created_at"),
        Index("ix_logs_agent", "agent_id"),
        Index("ix_logs_category", "category"),
        {"schema": "audit"},
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)

    # Who
    agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))
    user_id = Column(String(100))

    # What
    category = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(BigInteger)

    # Details
    level = Column(SQLEnum(LogLevel), default=LogLevel.INFO)
    message = Column(Text, nullable=False)
    details = Column(JSON, default={})

    # Context
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"))
    project_id = Column(BigInteger, ForeignKey("project.projects.id"))
    task_id = Column(BigInteger)
    review_id = Column(BigInteger)
    conversation_id = Column(BigInteger)

    # Request info
    request_id = Column(String(64))
    session_id = Column(BigInteger, ForeignKey("agent.sessions.id"))
    ip_address = Column(INET)
    user_agent = Column(Text)

    # Performance
    duration_ms = Column(Integer)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Escalation(Base):
    """Issues requiring human intervention."""
    __tablename__ = "escalations"
    __table_args__ = (
        Index("ix_escalations_status", "status"),
        {"schema": "audit"},
    )

    id = Column(BigInteger, Identity(always=True), primary_key=True)

    # What triggered escalation
    escalation_type = Column(String(50), nullable=False)

    # Context
    circle_id = Column(BigInteger, ForeignKey("circle.circles.id"))
    project_id = Column(BigInteger, ForeignKey("project.projects.id"))
    task_id = Column(BigInteger)
    review_id = Column(BigInteger)
    agent_id = Column(BigInteger, ForeignKey("agent.agents.id"))

    # Escalation details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    context = Column(JSON, default={})

    # Priority (1 = highest, 10 = lowest)
    priority = Column(Integer, default=5)
    severity = Column(String(20), default="medium")

    # Status
    status = Column(String(50), default="open")

    # Assignment
    assigned_to_user_id = Column(String(100))

    # Resolution
    resolution = Column(Text)
    resolution_type = Column(String(50))
    resolved_by_user_id = Column(String(100))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    due_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Escalation #{self.id} {self.escalation_type} status={self.status}>"
